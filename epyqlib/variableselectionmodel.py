import epyqlib.abstractcolumns
import epyqlib.cmemoryparser
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import json

from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot,
                          QTimer)

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
    def __init__(self, root, parent=None):
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
                path = []
                while node.tree_parent is not None:
                    path.insert(0, node.fields.name)
                    node = node.tree_parent
                selected.append(path)

        self.root.traverse(
            call_this=add_if_checked,
            payload=selected,
            internal_nodes=True
        )

        with open(filename, 'w') as f:
            json.dump(selected, f, indent='    ')

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


