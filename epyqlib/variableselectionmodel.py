import logging
logger = logging.getLogger(__name__)

import attr
import collections
import csv
import eliot
import epyqlib.abstractcolumns
import epyqlib.chunkedmemorycache as cmc
import epyqlib.cmemoryparser
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.twisted.cancalibrationprotocol as ccp
import epyqlib.utils.twisted
import functools
import io
import itertools
import json
import math
import sys
import textwrap
import time
import twisted.internet.defer
import twisted.internet.threads

from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot,
                          QTimer, QObject, QCoreApplication)
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
                 tree_parent=None, comparison_value=None):
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

        self.comparison_value = comparison_value

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
        while isinstance(node, type(self)):
            path.insert(0, node.fields.name)
            node = node.tree_parent

        return path

    def chunk_updated(self, data):
        self.fields.value = self.variable.unpack(data)

    def add_members(self, base_type, address, expand_pointer=False):
        new_members = []

        if isinstance(base_type, epyqlib.cmemoryparser.Struct):
            new_members.extend(
                self.add_struct_members(base_type, address))

        if isinstance(base_type, epyqlib.cmemoryparser.ArrayType):
            new_members.extend(
                self.add_array_members(base_type, address))

        if (expand_pointer and
                isinstance(base_type, epyqlib.cmemoryparser.PointerType)):
            new_members.extend(
                self.add_pointer_members(base_type, address))

        for child in self.children:
            new_members.extend(child.add_members(
                base_type=epyqlib.cmemoryparser.base_type(child.variable),
                address=child.address()
                # do not expand child pointers since we won't have their values
            ))

        return new_members

    def add_struct_members(self, base_type, address):
        new_members = []
        for name, member in base_type.members.items():
            child_address = address + base_type.offset_of([name])
            child_node = VariableNode(
                variable=member,
                name=name,
                address=child_address,
                bits=member.bit_size
            )
            self.append_child(child_node)
            new_members.append(child_node)

        return new_members

    def add_array_members(self, base_type, address):
        new_members = []
        format = '[{{:0{}}}]'.format(len(str(base_type.length())))
        for index in range(base_type.length()):
            child_address = address + base_type.offset_of(index)
            variable = epyqlib.cmemoryparser.Variable(
                name=format.format(index),
                type=base_type.type,
                address=child_address
            )
            child_node = VariableNode(variable=variable,
                                      comparison_value=index)
            self.append_child(child_node)
            new_members.append(child_node)

        return new_members

    def add_pointer_members(self, base_type, address):
        new_members = []
        target_type = epyqlib.cmemoryparser.base_type(base_type.type)
        if not isinstance(target_type, epyqlib.cmemoryparser.UnspecifiedType):
            variable = epyqlib.cmemoryparser.Variable(
                name='*{}'.format(self.fields.name),
                type=base_type.type,
                address=self.fields.value
            )
            child_node = VariableNode(variable=variable)
            self.append_child(child_node)
            new_members.append(child_node)

        return new_members


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


@attr.s
class AverageValueRate:
    _seconds = attr.ib(convert=float)
    _deque = attr.ib(default=attr.Factory(collections.deque))

    @attr.s
    class Event:
        time = attr.ib()
        value = attr.ib()
        delta = attr.ib()

    def add(self, value):
        now = time.monotonic()

        if len(self._deque) > 0:
            delta = now - self._deque[-1].time

            cutoff_time = now - self._seconds

            while self._deque[0].time < cutoff_time:
                self._deque.popleft()
        else:
            delta = 0

        event = self.Event(time=now, value=value, delta=delta)
        self._deque.append(event)

    def rate(self):
        if len(self._deque) > 0:
            dv = self._deque[-1].value - self._deque[0].value
            dt = self._deque[-1].time - self._deque[0].time
        else:
            dv = -1
            dt = 0

        if dv <= 0:
            return 0
        elif dt == 0:
            return math.inf

        return dv / dt

    def remaining_time(self, final_value):
        rate = self.rate()
        if rate <= 0:
            return math.inf
        else:
            return (final_value - self._deque[-1].value) / rate


class Progress(QObject):
    # TODO: CAMPid 7531968542136967546542452
    updated = pyqtSignal(int)
    completed = pyqtSignal()
    done = pyqtSignal()
    failed = pyqtSignal()
    canceled = pyqtSignal()

    default_progress_label = (
        '{elapsed} seconds elapsed, {remaining} seconds remaining'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.completed.connect(self.done)
        self.failed.connect(self.done)
        self.canceled.connect(self.done)

        self.done.connect(self._done)

        self.progress = None
        self.average = None
        self.average_timer = QTimer()
        self.average_timer.setInterval(200)
        self.average_timer.timeout.connect(self._update_time_estimate)
        self._label_text_replace = None
        self._start_time = None

    def _done(self):
        self.average_timer.stop()
        self.average = None

        self.updated.disconnect(self.progress.setValue)
        self.progress.close()
        self.progress = None

        self._start_time = None

    def _update_time_estimate(self):
        remaining = self.average.remaining_time(self.progress.maximum())
        try:
            remaining = round(remaining)
        except:
            pass
        self.progress.setLabelText(self._label_text_replace.format(
                elapsed=round(time.monotonic() - self._start_time),
                remaining=remaining
            )
        )

    def connect(self, progress, label_text=None):
        self.progress = progress

        if label_text is None:
            label_text = self.default_progress_label
        self._label_text_replace = label_text

        self.progress.setMinimumDuration(0)
        # Default to a busy indicator, progress maximum can be set later
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.updated.connect(self.progress.setValue)

        if self._start_time is None:
            self._start_time = time.monotonic()

        self.average = AverageValueRate(seconds=30)
        self.average_timer.start()

    def configure(self, minimum=0, maximum=0):
        self.progress.setMinimum(minimum)
        self.progress.setMaximum(maximum)

    def complete(self, message=None):
        if message is not None:
            QMessageBox.information(self.progress, 'EPyQ', message)

        self.completed.emit()

    def fail(self):
        self.failed.emit()

    def update(self, value):
        self.average.add(value)
        self.updated.emit(value)


class VariableModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    binary_loaded = pyqtSignal()

    def __init__(self, root, nvs, bus, parent=None):
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
        self.bus = bus

        self.bits_per_byte = None

        self.cache = None

        self.pull_log_progress = Progress()

        self.protocol = ccp.Handler(tx_id=0x1FFFFFFF, rx_id=0x1FFFFFF7)
        from twisted.internet import reactor
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.protocol,
            reactor=reactor,
            bus=self.bus)

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

    def update_from_loaded_binary(self, binary_info):
        names, variables, bits_per_byte = binary_info

        self.bits_per_byte = bits_per_byte
        self.names = names

        self.beginResetModel()

        self.root.children = []
        for variable in variables:
            QCoreApplication.processEvents()

            node = VariableNode(variable=variable)
            self.root.append_child(node)
            node.add_members(
                base_type=epyqlib.cmemoryparser.base_type(variable),
                address=variable.address
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
                     include_partially_checked=False, test=None):
        def default_test(node):
            acceptable_states = {
                Qt.Unchecked,
                Qt.PartiallyChecked,
                Qt.Checked
            }

            if only_checked:
                acceptable_states.discard(Qt.Unchecked)

                if not include_partially_checked:
                    acceptable_states.discard(Qt.PartiallyChecked)

            return node.checked() in acceptable_states

        if test is None:
            test = default_test

        cache = cmc.Cache(bits_per_byte=self.bits_per_byte)

        def update_parameter(node, cache):
            QCoreApplication.processEvents()

            if node is self.root:
                return

            if test(node):
                # TODO: CAMPid 0457543543696754329525426
                chunk = cache.new_chunk(
                    address=int(node.fields.address, 16),
                    bytes=b'\x00' * node.fields.size * (self.bits_per_byte // 8),
                    reference=node
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

        if isinstance(node.variable.type,
                      epyqlib.cmemoryparser.PointerType):
            # http://doc.qt.io/qt-5/qabstractitemmodel.html#layoutChanged
            # TODO: review other uses of layoutChanged and possibly 'correct' them
            self.layoutAboutToBeChanged.emit()
            index = self.index_from_node(node)
            for row, child in enumerate(node.children):
                self.unsubscribe(node=child, recurse=True)
                node.remove_child(row=row)
            new_members = node.add_members(
                base_type=epyqlib.cmemoryparser.base_type(node.variable.type),
                address=node.address(),
                expand_pointer=True
            )
            self.changePersistentIndex(
                index,
                self.index_from_node(node)
            )
            self.layoutChanged.emit()

            for node in new_members:
                # TODO: CAMPid 0457543543696754329525426
                chunk = self.cache.new_chunk(
                    address=int(node.fields.address, 16),
                    bytes=b'\x00' * node.fields.size * (self.bits_per_byte // 8),
                    reference=node
                )
                self.cache.add(chunk)

                self.subscribe(node=node, chunk=chunk)

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
    def get_chunks(self):
        chunks_path = ['dataLoggerParams', 'chunks']
        chunks_node = self.get_variable_node(*chunks_path)
        chunks = []
        for chunk_node in chunks_node.children:
            index_path = chunks_path + [chunk_node.fields.name]
            chunk_address = (
                yield self.get_variable_value(*index_path, 'address')
            )
            chunk_bytes = yield self.get_variable_value(*index_path, 'bytes')
            chunks.append((chunk_address, chunk_bytes))

        twisted.internet.defer.returnValue(chunks)

    def pull_log(self, csv_path):
        d = self._pull_log(csv_path)

        d.addErrback(epyqlib.utils.twisted.detour_result,
                     self.pull_log_progress.fail)
        d.addErrback(epyqlib.utils.twisted.errbackhook)

    @twisted.internet.defer.inlineCallbacks
    def _pull_log(self, csv_path):
        record_count = yield self.get_variable_value('dataLogger_block', 'validRecordCount')
        chunk_ranges = yield self.get_chunks()

        def overlaps_a_chunk(node):
            if len(node.children) > 0:
                return False

            node_lower = int(node.fields.address, 16)
            node_upper = node_lower + node.fields.size - 1

            for lower, upper in chunk_ranges:
                upper = lower + upper - 1
                if lower <= node_upper and upper >= node_lower:
                    return True

            return False

        cache = self.create_cache(test=overlaps_a_chunk)

        chunks = cache.contiguous_chunks()

        record_length = self.record_header_length()
        for chunk in chunks:
            record_length += len(chunk)

        # TODO: check against block.recordLength from module

        octets = self.block_header_length() + record_count * record_length
        self.pull_log_progress.configure(maximum=octets)

        # TODO: hardcoded station address, tsk-tsk
        yield self.protocol.connect(station_address=0)
        data = yield self.protocol.upload_block(
            address_extension=ccp.AddressExtension.data_logger,
            address=0,
            octets=octets,
            progress=self.pull_log_progress
        )
        yield self.protocol.disconnect()

        seconds = time.monotonic() - self.pull_log_progress._start_time

        self.pull_log_progress.configure()
        yield self.parse_log(
            data=data,
            cache=cache,
            chunks=chunks,
            csv_path=csv_path
        )

        completed_format = textwrap.dedent('''\
        Log successfully pulled

        Data time: {seconds:.3f} seconds for {bytes} bytes or {bps:.0f} bytes/second''')
        message = completed_format.format(
            seconds=seconds,
            bytes=octets,
            bps=octets / seconds
        )

        print(message)

        self.pull_log_progress.complete(message=message)

    def record_header_length(self):
        return (self.names['DataLogger_RecordHeader'].type.bytes
                * (self.bits_per_byte // 8))

    def block_header_length(self):
        try:
            block_header = self.names['DataLogger_BlockHeader']
        except KeyError:
            block_header_bytes = 0
        else:
            block_header_bytes = block_header.type.bytes

        return block_header_bytes * (self.bits_per_byte // 8)

    def parse_log(self, data, cache, chunks, csv_path):
        data_stream = io.BytesIO(data)

        if self.block_header_length() > 0:
            raise Exception('Code needs to be updated to handle a non-empty '
                            'block header.')

        acceptable_states = {Qt.Checked, Qt.PartiallyChecked}

        def collect_variables(node, payload):
            if node.checked() in acceptable_states:
                payload.append(node)

        # TODO: hardcoded 32-bit addressing and offset assumption
        #       intended to avoid collision
        record_header_address = 2**32 + 100
        record_header = epyqlib.cmemoryparser.Variable(
            name='.record_header',
            type=self.names['DataLogger_RecordHeader'],
            address=record_header_address
        )
        record_header_node = VariableNode(variable=record_header)
        record_header_node.add_members(
            base_type=epyqlib.cmemoryparser.base_type(record_header),
            address=record_header.address
        )
        for node in record_header_node.leaves():
            chunk = cache.new_chunk(
                address=int(node.fields.address, 16),
                bytes=b'\x00' * node.fields.size
                      * (self.bits_per_byte // 8),
                reference=node
            )
            cache.add(chunk)
        record_header_chunk = cache.new_chunk(
                address=int(record_header_node.fields.address, 16),
                bytes=b'\x00' * record_header_node.fields.size
                      * (self.bits_per_byte // 8)
            )

        chunks.insert(0, record_header_chunk)

        variables_and_chunks = {chunk.reference: chunk
                                for chunk in cache._chunks}

        rows = []

        try:
            while data_stream.tell() < len(data):
                QCoreApplication.processEvents()
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

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=sorted(rows[0].keys(), key=str.casefold)
            )
            writer.writeheader()

            for row in rows:
                writer.writerow(row)

    def get_variable_node(self, *variable_path):
        variable = self.root

        for name in variable_path:
            if name is None:
                raise TypeError('Unable to search by None')

            variable = next(v for v in variable.children
                            if name in (v.fields.name, v.comparison_value))

        return variable

    def get_variable_nodes_by_type(self, type_name):
        return (node for node in self.root.children
                if node.fields.type == type_name)

    @twisted.internet.defer.inlineCallbacks
    def get_variable_value(self, *variable_path):
        variable = self.get_variable_node(*variable_path)
        value = yield self._get_variable_value(variable)

        twisted.internet.defer.returnValue(value)

    @twisted.internet.defer.inlineCallbacks
    def _get_variable_value(self, variable):
        # TODO: hardcoded station address, tsk-tsk
        yield self.protocol.connect(station_address=0)
        data = yield self.protocol.upload_block(
            address_extension=ccp.AddressExtension.raw,
            address=variable.address(),
            octets=variable.fields.size * (self.bits_per_byte // 8)
        )
        yield self.protocol.disconnect()

        value = variable.variable.unpack(data)

        twisted.internet.defer.returnValue(value)

    def subscribe(self, node, chunk):
        callback = functools.partial(
            self.update_chunk,
            node=node,
        )
        self.cache.subscribe(callback, chunk, reference=node)

    def unsubscribe(self, node, recurse=True):
        self.cache.unsubscribe_by_reference(reference=node)

        if recurse:
            for child in node.children:
                self.unsubscribe(node=child, recurse=recurse)

    def read(self, variable):
        action = eliot.start_task(action_type='Read variable')
        with action.context():
            d = eliot.twisted.DeferredContext(self._read(variable))
            # ?? epyqlib.utils.twisted.errbackhook
            d.addErrback(eliot.write_failure)
            d.addActionFinish()

            return d.result

    @twisted.internet.defer.inlineCallbacks
    def _read(self, variable):
        # TODO: just call get_variable_value()?
        chunk = self.cache.new_chunk(
            address=int(variable.fields.address, 16),
            bytes=b'\x00' * variable.fields.size * (self.bits_per_byte // 8)
        )

        # TODO: hardcoded station address, tsk-tsk
        yield self.protocol.connect(station_address=0)
        data = yield self.protocol.upload_block(
            address_extension=ccp.AddressExtension.raw,
            address=variable.address(),
            octets=variable.fields.size * (self.bits_per_byte // 8)
        )
        yield self.protocol.disconnect()

        chunk.set_bytes(data)
        self.cache.update(update_chunk=chunk)
