import collections
import csv
import epyqlib.abstractcolumns
import epyqlib.chunkedmemorycache as cmc
import epyqlib.cmemoryparser
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.twisted.cancalibrationprotocol as ccp
import functools
import io
import itertools
import json
import queue
import threading
import twisted

from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot,
                          QTimer, QObject)
from PyQt5.QtWidgets import QMessageBox

# See file COPYING in this source tree
from _pytest.junitxml import record_xml_property

__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(epyqlib.abstractcolumns.AbstractColumns):
    _members = ['name', 'type', 'address', 'size', 'bits', 'value']

Columns.indexes = Columns.indexes()


class VariableNode(epyqlib.treenode.TreeNode):
    def __init__(self, variable, name=None, address=None, bits=None,
                 tree_parent=None):
        epyqlib.treenode.TreeNode.__init__(self, parent=tree_parent)

        self.variable = variable
        name = name if name is not None else variable.name
        address = address if address is not None else variable.address
        if bits is None:
            bits = ''

        base_type = epyqlib.cmemoryparser.base_type(variable)
        type_name = epyqlib.cmemoryparser.type_name(variable)

        self.fields = Columns(name=name,
                              type=type_name,
                              address='0x{:08X}'.format(address),
                              size=base_type.bytes,
                              bits=bits,
                              value=None)

        self._checked = Columns.fill(Qt.Unchecked)

    def unique(self):
        return id(self)

    def checked(self, column=Columns.indexes.name):
        return self._checked[column]

    def set_checked(self, checked, column=Columns.indexes.name):
        was_checked = self._checked[column]
        self._checked[column] = checked

        if was_checked != checked and Qt.Checked in [was_checked, checked]:
            if self.tree_parent.tree_parent is None:
                self.update_checks()
            else:
                self.tree_parent.update_checks()

    def address(self):
        return int(self.fields.address, 16)

    def addresses(self):
        address = self.address()
        return [address + offset for offset in range(self.fields.size)]

    def update_checks(self):
        def append_address(node, addresses):
            if node.checked() == Qt.Checked:
                addresses |= set(node.addresses())

        addresses = set()

        top_ancestor = self
        while top_ancestor.tree_parent.tree_parent is not None:
            top_ancestor = top_ancestor.tree_parent

        top_ancestor.traverse(
            call_this=append_address,
            payload=addresses,
            internal_nodes=True
        )

        def set_partially_checked(node, _):
            if node.checked() != Qt.Checked:
                if not set(node.addresses()).isdisjoint(addresses):
                    check = Qt.PartiallyChecked
                else:
                    check = Qt.Unchecked

                node.set_checked(check)

        self.traverse(call_this=set_partially_checked, internal_nodes=True)

        ancestor = self
        while ancestor.tree_parent is not None:
            if ancestor.checked() != Qt.Checked:
                if not set(ancestor.addresses()).isdisjoint(addresses):
                    change_to = Qt.PartiallyChecked
                else:
                    change_to = Qt.Unchecked

                ancestor.set_checked(change_to)

            ancestor = ancestor.tree_parent

    def path(self):
        path = []
        node = self
        while node.tree_parent is not None:
            path.insert(0, node.fields.name)
            node = node.tree_parent

        return path

    def chunk_updated(self, data):
        self.fields.value = self.variable.unpack(data)


class Variables(epyqlib.treenode.TreeNode):
    # TODO: just Rx?
    changed = pyqtSignal(epyqlib.treenode.TreeNode, int,
                         epyqlib.treenode.TreeNode, int,
                         list)
    begin_insert_rows = pyqtSignal(epyqlib.treenode.TreeNode, int, int)
    end_insert_rows = pyqtSignal()

    def __init__(self):
        epyqlib.treenode.TreeNode.__init__(self)

        self.fields = Columns.fill('')

    def unique(self):
        return id(self)


class Progress(QObject):
    # TODO: CAMPid 7531968542136967546542452
    updated = pyqtSignal(int)
    completed = pyqtSignal()
    done = pyqtSignal()
    failed = pyqtSignal()
    canceled = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.completed.connect(self.done)
        self.failed.connect(self.done)
        self.canceled.connect(self.done)

        self.done.connect(self._done)

        self.progress = None

    def _done(self):
        self.updated.disconnect(self.progress.setValue)
        self.progress = None

    def connect(self, progress):
        self.progress = progress

        self.progress.setMinimumDuration(0)
        # Default to a busy indicator, progress maximum can be set later
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.updated.connect(self.progress.setValue)

    def configure(self, minimum=0, maximum=0):
        self.progress.setMinimum(minimum)
        self.progress.setMaximum(maximum)

    def complete(self):
        self.completed.emit()

    def update(self, value):
        self.updated.emit(value)


class VariableModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    binary_loaded = pyqtSignal()

    def __init__(self, root, nvs, parent=None):
        checkbox_columns = Columns.fill(False)
        checkbox_columns.name = True

        epyqlib.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, checkbox_columns=checkbox_columns,
                parent=parent)

        self.headers = Columns(
            name='Name',
            type='Type',
            address='Address',
            size='Size',
            bits='Bits',
            value='Value'
        )

        self.root = root
        self.nvs = nvs

        # TODO: quit hardcoding bits per byte
        self.bits_per_byte = 16

        self.cache = None

        self.load_binary_timer = QTimer()
        self.load_binary_timer.setSingleShot(True)
        self.load_binary_timer.setInterval(200)
        self.load_binary_timer.timeout.connect(self.load_binary_post)

        self.load_binary_thread = None
        self.load_binary_queue = None

        self.pull_log_progress = Progress()

    def setData(self, index, data, role=None):
        if index.column() == Columns.indexes.name:
            if role == Qt.CheckStateRole:
                node = self.node_from_index(index)

                node.set_checked(data)

                # TODO: CAMPid 9349911217316754793971391349
                parent = node.tree_parent
                self.changed(parent.children[0], Columns.indexes.name,
                             parent.children[-1], Columns.indexes.name,
                             [Qt.CheckStateRole])

                return True

    def load_binary(self, filename):
        self.load_binary_queue = queue.Queue(1)

        self.load_binary_thread = threading.Thread(
            target=epyqlib.cmemoryparser.process_file,
            kwargs={
                'filename': filename,
                'queue': self.load_binary_queue
            }
        )

        self.load_binary_timer.start()
        self.load_binary_thread.start()

    def load_binary_post(self):
        try:
            names, variables, bits_per_byte = (
                self.load_binary_queue.get_nowait())
        except queue.Empty:
            self.load_binary_timer.start()
            return

        self.load_binary_thread.join(timeout=2)
        if self.load_binary_thread.is_alive():
            # TODO: notify someone?
            pass
        self.load_binary_thread = None
        self.load_binary_queue = None

        self.beginResetModel()

        self.root.children = []
        for variable in variables:
            node = VariableNode(variable=variable)
            self.root.append_child(node)
            self.add_struct_members(
                base_type=epyqlib.cmemoryparser.base_type(variable),
                address=variable.address,
                node=node
            )

        self.endResetModel()

        self.cache = self.create_cache(only_checked=False, subscribe=True)

        self.binary_loaded.emit()

    def save_selection(self, filename):
        selected = []

        def add_if_checked(node, selected):
            if node is self.root:
                return

            if node.checked() == Qt.Checked:
                selected.append(node.path())

        self.root.traverse(
            call_this=add_if_checked,
            payload=selected,
            internal_nodes=True
        )

        with open(filename, 'w') as f:
            json.dump(selected, f, indent='    ')

    def load_selection(self, filename):
        with open(filename, 'r') as f:
            selected = json.load(f)

        def check_if_selected(node, _):
            if node is self.root:
                return

            if node.path() in selected:
                node.set_checked(Qt.Checked)

        self.root.traverse(
            call_this=check_if_selected,
            internal_nodes=True
        )

    def create_cache(self, only_checked=True, subscribe=False,
                     include_partially_checked=False):
        cache = cmc.Cache(bits_per_byte=self.bits_per_byte)

        def update_parameter(node, cache):
            if node is self.root:
                return

            acceptable_states = {
                Qt.Unchecked,
                Qt.PartiallyChecked,
                Qt.Checked
            }

            if only_checked:
                acceptable_states.discard(Qt.Unchecked)

                if not include_partially_checked:
                    acceptable_states.discard(Qt.PartiallyChecked)

            if node.checked() in acceptable_states:
                chunk = cache.new_chunk(
                    address=int(node.fields.address, 16),
                    bytes=b'\x00' * node.fields.size * (self.bits_per_byte // 8)
                )
                cache.add(chunk)

                if subscribe:
                    callback = functools.partial(
                        self.update_chunk,
                        node=node,
                    )
                    cache.subscribe(callback, chunk)

        self.root.traverse(
            call_this=update_parameter,
            payload=cache,
            internal_nodes=True
        )

        return cache

    def update_chunk(self, data, node):
        node.chunk_updated(data)

        self.changed(node, Columns.indexes.value,
                     node, Columns.indexes.value,
                     roles=[Qt.DisplayRole])

    def update_parameters(self):
        cache = self.create_cache()

        set_frames = self.nvs.logger_set_frames()

        chunks = cache.contiguous_chunks()

        frame_count = len(set_frames)
        chunk_count = len(chunks)
        if chunk_count > frame_count:
            chunks = chunks[:frame_count]

            message_box = QMessageBox()
            message_box.setStandardButtons(QMessageBox.Ok)

            text = ("Variable selection yields {chunks} memory chunks but "
                    "is limited to {frames}.  Selection has been truncated."
                    .format(chunks=chunk_count, frames=frame_count))

            message_box.setText(text)

            message_box.exec()

        for chunk, frame in itertools.zip_longest(
                chunks, set_frames, fillvalue=cache.new_chunk(0, 0)):
            print('{address}+{size}'.format(
                address='0x{:08X}'.format(chunk._address),
                size=len(chunk._bytes) // (self.bits_per_byte // 8)
            ))

            address_signal = frame.signal_by_name('Address')
            bytes_signal = frame.signal_by_name('Bytes')

            address_signal.set_value(chunk._address)
            bytes_signal.set_value(
                len(chunk._bytes) // (self.bits_per_byte // 8))

    @twisted.internet.defer.inlineCallbacks
    def read_range(self, address_extension, address, octets, progress=None):
        protocol = ccp.Handler(tx_id=0x1FFFFFFF, rx_id=0x1FFFFFF7)
        from twisted.internet import reactor
        transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=protocol,
            reactor=reactor,
            bus=self.nvs.bus.bus)
        # TODO: whoa! cheater!  stealing a bus like that

        yield protocol.connect(station_address=0)
        # TODO: hardcoded extension, tsk-tsk
        yield protocol.set_mta(
            address=address,
            address_extension=address_extension
        )

        data = bytearray()

        remaining = octets
        while remaining > 0:
            number_of_bytes = min(4, remaining)
            block = yield protocol.upload(number_of_bytes=number_of_bytes)
            remaining -= number_of_bytes

            if progress is not None:
                progress.update(octets - remaining)

            data.extend(block)

        twisted.internet.defer.returnValue(data)

    def pull_log(self, csv_path):
        d = self.get_variable_value('block', 'validRecordCount')

        cache = self.create_cache()

        chunks = cache.contiguous_chunks()

        record_length = self.record_header_length()
        for chunk in chunks:
            record_length += len(chunk)

        # TODO: check against block.recordLength from module

        # TODO: add download progress indicator

        def octets_and_configure(n):
            octets = self.block_header_length() + n * record_length
            self.pull_log_progress.configure(maximum=octets)
            return octets

        d.addCallback(octets_and_configure)
        d.addCallback(lambda octets: self.read_range(
            address_extension=ccp.AddressExtension.data_logger,
            address=0,
            octets=octets,
            progress=self.pull_log_progress
        ))

        def pass_first(result, function, *args, **kwargs):
            function(*args, **kwargs)
            return result

        d.addCallback(pass_first, self.pull_log_progress.configure)
        d.addCallback(self.parse_log, cache=cache, chunks=chunks,
                      csv_path=csv_path)
        d.addCallback(lambda _: self.pull_log_progress.complete())
        d.addErrback(print)

    def record_header_length(self):
        # TODO: hardcoded, either add a global header or figure it out
        #       from the already parsed variables (need to get structure
        #       definitions directly?)
        return 1 * (self.bits_per_byte // 8)

    def block_header_length(self):
        # TODO: hardcoded, either add a global header or figure it out
        #       from the already parsed variables (need to get structure
        #       definitions directly?)
        return 0 * (self.bits_per_byte // 8)

    def parse_log(self, data, cache, chunks, csv_path):
        print('about to parse: {}'.format(data))

        data_stream = io.BytesIO(data)

        # TODO: what about the (for now empty) block header?

        acceptable_states = {Qt.Checked, Qt.PartiallyChecked}

        def collect_variables(node, payload):
            if node.checked() in acceptable_states:
                payload.append(node)

        variable_list = []
        self.root.traverse(collect_variables, variable_list)

        # TODO: since this is a variable like $P$T0$2 we probably shouldn't
        #       be using it so find another way to handle this
        record_header_node = next(
            self.get_variable_nodes_by_type('DataLogger_RecordHeader'))
        record_header_nodes = [c for c in record_header_node.children]
        variable_list = record_header_nodes + variable_list
        record_header_chunk = cache.new_chunk(
                address=int(record_header_node.fields.address, 16),
                bytes=b'\x00' * record_header_node.fields.size
                      * (self.bits_per_byte // 8)
            )

        chunks.insert(0, record_header_chunk)

        variables_and_chunks = {
            variable: cache.new_chunk(
                address=int(variable.fields.address, 16),
                bytes=b'\x00' * variable.fields.size * (self.bits_per_byte // 8)
            )
            for variable in variable_list
        }

        for chunk in variables_and_chunks.values():
            cache.add(chunk)

        rows = []

        try:
            while data_stream.tell() < len(data):
                row = collections.OrderedDict()

                def update(data, variable):
                    path = '.'.join(variable.path())
                    row[path] = variable.variable.unpack(data)

                for variable, chunk in variables_and_chunks.items():
                    partial = functools.partial(
                        update,
                        variable=variable
                    )
                    cache.subscribe(partial, chunk)

                for chunk in chunks:
                    chunk_bytes = bytearray(
                        data_stream.read(len(chunk)))
                    if len(chunk_bytes) != len(chunk):
                        raise EOFError(
                            'Unexpected EOF found in the middle of a record')

                    chunk.set_bytes(chunk_bytes)
                    cache.update(chunk)

                cache.unsubscribe_all()
                rows.append(row)
        except EOFError:
            message_box = QMessageBox()
            message_box.setStandardButtons(QMessageBox.Ok)

            text = ("Unexpected EOF found in the middle of a record.  "
                    "Continuing with partially extracted log.")

            message_box.setText(text)

            message_box.exec()

        with open(csv_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()

            for row in rows:
                writer.writerow(row)

    def add_struct_members(self, base_type, address, node):
        if isinstance(base_type, epyqlib.cmemoryparser.Struct):
            for name, member in base_type.members.items():
                child_address = address + base_type.offset_of([name])
                child_node = VariableNode(
                    variable=member,
                    name=name,
                    address=child_address,
                    bits=member.bit_size
                )
                node.append_child(child_node)

                self.add_struct_members(
                    base_type=epyqlib.cmemoryparser.base_type(member),
                    address=child_address,
                    node=child_node
                )

    def get_variable_node(self, *variable_path):
        variable = self.root

        for name in variable_path:
            variable = next(v for v in variable.children
                            if v.fields.name == name)

        return variable

    def get_variable_nodes_by_type(self, type_name):
        return (node for node in self.root.children
                if node.fields.type == type_name)

    @twisted.internet.defer.inlineCallbacks
    def get_variable_value(self, *variable_path):
        variable = self.get_variable_node(*variable_path)
        value = yield self._read(variable)

        twisted.internet.defer.returnValue(value)

    @twisted.internet.defer.inlineCallbacks
    def _read(self, variable):
        data = yield self.read_range(
            address_extension=ccp.AddressExtension.raw,
            address=variable.address(),
            octets=variable.fields.size * (self.bits_per_byte // 8)
        )

        value = variable.variable.unpack(data)

        twisted.internet.defer.returnValue(value)

    def read(self, variable):
        chunk = self.cache.new_chunk(
            address=int(variable.fields.address, 16),
            bytes=b'\x00' * variable.fields.size * (self.bits_per_byte // 8)
        )

        d = self.read_range(
            address_extension=ccp.AddressExtension.raw,
            address=variable.address(),
            octets=variable.fields.size * (self.bits_per_byte // 8)
        )

        d.addCallback(chunk.set_bytes)
        d.addCallback(lambda _: self.cache.update(update_chunk=chunk))
        d.addErrback(print)
