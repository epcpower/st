import epyqlib.abstractcolumns
import epyqlib.cmemoryparser
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode

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

        self.fields = Columns(name=name,
                              type=variable.type,
                              address='0x{:08X}'.format(address),
                              size=epyqlib.cmemoryparser.base_type(variable).bytes,
                              bits=bits)

    def unique(self):
        return id(self)


class Variables(epyqlib.treenode.TreeNode):
    # TODO: just Rx?
    changed = pyqtSignal(epyqlib.treenode.TreeNode, int,
                         epyqlib.treenode.TreeNode, int,
                         list)
    begin_insert_rows = pyqtSignal(epyqlib.treenode.TreeNode, int, int)
    end_insert_rows = pyqtSignal()

    def __init__(self):
        epyqlib.treenode.TreeNode.__init__(self)

        # TODO: this should probably be done in the view but this is easier for now
        self.children.sort(key=lambda c: c.name)

        self.fields = Columns.fill('')

    def unique(self):
        return id(self)


class VariableModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, parent=None):
        checkbox_columns = Columns.fill(False)

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


