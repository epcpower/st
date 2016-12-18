import epyqlib.abstractcolumns
import epyqlib.chunkedmemorycache as cmc
import epyqlib.cmemoryparser
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.twisted.cancalibrationprotocol as ccp
import itertools
import json

from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot,
                          QTimer)
from PyQt5.QtWidgets import QMessageBox

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(epyqlib.abstractcolumns.AbstractColumns):
    _members = ['name', 'type', 'address', 'size', 'bits']

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
                              bits=bits)

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

    def addresses(self):
        address = int(self.fields.address, 16)
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
            bits='Bits'
        )

        self.root = root
        self.nvs = nvs

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
        names, variables, bits_per_byte =\
            epyqlib.cmemoryparser.process_file(filename)

        self.root = Variables()
        for variable in variables:
            node = VariableNode(variable=variable)
            self.root.append_child(node)
            self.add_struct_members(
                base_type=epyqlib.cmemoryparser.base_type(variable),
                address=variable.address,
                node=node
            )

        self.modelReset.emit()

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

    def update_parameters(self):
        # TODO: quit hardcoding bits per byte
        cache = cmc.Cache(bits_per_byte=16)

        def update_parameter(node, cache):
            if node is self.root:
                return

            if node.checked() == Qt.Checked:
                print('{path}: {address}+{size}'.format(
                    path='.'.join(node.path()),
                    address=node.fields.address,
                    size=node.fields.size
                ))

                chunk = cache.new_chunk(
                    address=int(node.fields.address, 16),
                    bytes=b'\x00' * node.fields.size
                )
                cache.add(chunk)

        self.root.traverse(
            call_this=update_parameter,
            payload=cache,
            internal_nodes=True
        )

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
                size=len(chunk._bytes)
            ))

            address_signal = frame.signal_by_name('Address')
            bytes_signal = frame.signal_by_name('Bytes')

            address_signal.set_value(chunk._address)
            bytes_signal.set_value(len(chunk._bytes))

    def pull_log(self):
        protocol = ccp.Handler(tx_id=0x1FFFFFFF, rx_id=0x1FFFFFF7)
        from twisted.internet import reactor
        transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=protocol,
            reactor=reactor,
            bus=self.nvs.bus.bus)
        # TODO: whoa! cheater!  stealing a bus like that

        d = protocol.connect(station_address=0)
        # TODO: hardcoded extension, tsk-tsk
        d.addCallback(lambda _: protocol.set_mta(
            address=0,
            address_extension=ccp.AddressExtension.data_logger)
        )
        d.addCallback(lambda _: protocol.upload(
            container=bytearray(),
            number_of_bytes=4)
        )

        # TODO: figure out how many need to be read
        for _ in range(10):
            d.addCallback(protocol.upload, number_of_bytes=4)

        d.addCallback(print)
        d.addErrback(print)

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


