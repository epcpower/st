import logging
logger = logging.getLogger(__name__)

import attr
import epyqlib.abstractcolumns
import epyqlib.chunkedmemorycache as cmc
import epyqlib.cmemoryparser
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.twisted.cancalibrationprotocol as ccp
import epyqlib.twisted.nvs as nv_protocol
import epyqlib.utils.qt
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

        maximum_children = 256

        for index in range(base_type.length())[:maximum_children]:
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

        if base_type.length() > maximum_children:
            message = ('Arrays over {} elements are truncated.\n'
                       'This has happened to `{}`.'.format(
                maximum_children, self.fields.name
            ))
            QMessageBox.information(
                None,
                'EPyQ',
                message
            )

            # TODO: add a marker showing visually that it has been truncated

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

    def get_node(self, *variable_path, root=None):
        if root is None:
            root = self

        variable = root

        for name in variable_path:
            if name is None:
                raise TypeError('Unable to search by None')

            variable, = (v for v in variable.children
                         if name in (v.fields.name, v.comparison_value))

        return variable


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


class VariableModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    binary_loaded = pyqtSignal()

    def __init__(self, nvs, bus, parent=None):
        checkbox_columns = Columns.fill(False)
        checkbox_columns.name = True

        root = epyqlib.variableselectionmodel.Variables()

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

        self.nvs = nvs
        self.bus = bus

        self.bits_per_byte = None

        self.cache = None

        self.pull_log_progress = epyqlib.utils.qt.Progress()

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

    @twisted.internet.defer.inlineCallbacks
    def update_from_loaded_binary(self, binary_info):
        names, variables, bits_per_byte = binary_info

        self.bits_per_byte = bits_per_byte
        self.names = names

        self.beginResetModel()
        logger.debug('Updating from binary, {} variables'.format(len(variables)))

        self.root = yield twisted.internet.threads.deferToThread(
            self.build_node_tree,
           variables=variables
        )

        self.endResetModel()

        logger.debug('Creating cache')
        self.cache = self.create_cache(only_checked=False, subscribe=True)

        logger.debug('Done creating cache')
        self.binary_loaded.emit()

    def build_node_tree(self, variables):
        root = epyqlib.variableselectionmodel.Variables()

        for variable in variables:
            node = VariableNode(variable=variable)
            root.append_child(node)
            node.add_members(
                base_type=epyqlib.cmemoryparser.base_type(variable),
                address=variable.address
            )

        return root

    def assign_root(self, root):
        self.root = root

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
            # TODO: find a real solution to avoid blocking UI
            # QCoreApplication.processEvents()

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

    def update_parameters(self, parent=None):
        cache = self.create_cache()

        set_frames = self.nvs.logger_set_frames()

        chunks = cache.contiguous_chunks()

        frame_count = len(set_frames)
        chunk_count = len(chunks)
        if chunk_count > frame_count:
            chunks = chunks[:frame_count]

            message_box = QMessageBox(parent=parent)
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

    def parse_log(self, data, csv_path):
        data_stream = io.BytesIO(data)
        raw_header = data_stream.read(self.block_header_length())

        block_header_node = self.parse_block_header_into_node(
            raw_header=raw_header,
            bits_per_byte=self.bits_per_byte,
            block_header_type=self.names['DataLogger_BlockHeader']
        )

        cache = self.create_log_cache(block_header_node)

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

        chunks = sorted(
            cache.contiguous_chunks(),
            key=lambda c: (c._address != record_header_address, c)
        )

        variables_and_chunks = {chunk.reference: chunk
                                for chunk in cache._chunks}

        d = twisted.internet.threads.deferToThread(
            epyqlib.datalogger.parse_log,
            cache=cache,
            chunks=chunks,
            csv_path=csv_path,
            data_stream=data_stream,
            variables_and_chunks=variables_and_chunks
        )

        return d

    def create_log_cache(self, block_header_node):
        chunk_ranges = []
        chunks_node = block_header_node.get_node('chunks')
        for chunk in chunks_node.children:
            address = chunk.get_node('address')
            address = address.fields.value
            size = chunk.get_node('bytes')
            size = size.fields.value
            chunk_ranges.append((address, size))

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

        cache = self.create_cache(test=overlaps_a_chunk, subscribe=False)
        return cache

    def parse_block_header_into_node(self, raw_header, bits_per_byte, block_header_type):
        # TODO: hardcoded 32-bit addressing and offset assumption
        #       intended to avoid collision
        block_header_cache = cmc.Cache(bits_per_byte=bits_per_byte)
        block_header = epyqlib.cmemoryparser.Variable(
            name='.block_header',
            type=block_header_type,
            address=0
        )
        block_header_node = VariableNode(variable=block_header)
        block_header_node.add_members(
            base_type=epyqlib.cmemoryparser.base_type(block_header),
            address=block_header.address
        )
        for node in block_header_node.leaves():
            chunk = block_header_cache.new_chunk(
                address=int(node.fields.address, 16),
                bytes=b'\x00' * node.fields.size
                      * (bits_per_byte // 8),
                reference=node
            )
            block_header_cache.add(chunk)

            block_header_cache.subscribe(node.chunk_updated, chunk)
        block_header_chunk = block_header_cache.new_chunk(
            address=int(block_header_node.fields.address, 16),
            bytes=b'\x00' * block_header_node.fields.size
                  * (bits_per_byte // 8)
        )
        block_header_chunk.set_bytes(raw_header)
        block_header_cache.update(block_header_chunk)
        return block_header_node

    def get_variable_nodes_by_type(self, type_name):
        return (node for node in self.root.children
                if node.fields.type == type_name)

    @twisted.internet.defer.inlineCallbacks
    def get_variable_value(self, *variable_path):
        variable = self.root.get_node(*variable_path)
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
        d = self._read(variable)
        d.addErrback(epyqlib.utils.twisted.errbackhook)

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
