#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import weakref

from epyqlib.treenode import TreeNode
from PyQt5.QtCore import (Qt, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSignal, pyqtSlot)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


unique_role = Qt.UserRole


class PyQAbstractItemModel(QAbstractItemModel):
    root_changed = pyqtSignal(TreeNode)

    def __init__(self, root, checkbox_columns=None, editable_columns=None,
                 alignment=None, parent=None):
        QAbstractItemModel.__init__(self, parent=parent)

        self.root = root
        self.checkbox_columns = checkbox_columns
        self.editable_columns = editable_columns

        if alignment is not None:
            self.alignment = alignment
        else:
            self.alignment = Qt.AlignTop | Qt.AlignLeft


        self.index_from_node_cache = weakref.WeakKeyDictionary()

        self.role_functions = {
            Qt.DisplayRole: self.data_display,
            unique_role: self.data_unique,
            Qt.TextAlignmentRole: lambda index: int(self.alignment),
            Qt.CheckStateRole: self.data_check_state,
            Qt.EditRole: self.data_edit,
            Qt.BackgroundRole: self.data_background,
            Qt.DecorationRole: self.data_decoration,
            Qt.ToolTipRole: self.data_tool_tip,
            Qt.FontRole: self.data_font,
        }

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

    def data_display(self, index):
        node = index.internalPointer()

        column = index.column()
        if column < len(node.fields):
            return node.fields[column]

        return None

    def data_unique(self, index):
        return index.internalPointer().unique()

    def data_check_state(self, index):
        if self.checkbox_columns is not None:
            if self.checkbox_columns[index.column()]:
                node = index.internalPointer()
                if hasattr(node, 'checked'):
                    return node.checked(index.column())

                return None

    def data_edit(self, index):
        node = index.internalPointer()
        if hasattr(node, 'get_human_value'):
            if callable(node.get_human_value):
                value = node.get_human_value()
            else:
                value = ''
        else:
            value = node.fields[index.column()]

        if value is None:
            value = ''
        else:
            value = str(value)

        return value

    def data_background(self, index):
        return None

    def data_decoration(self, index):
        return None

    def data_tool_tip(self, index):
        return None

    def data_font(self, index):
        return None

    def data(self, index, role):
        if not index.isValid():
            return None

        if role in self.role_functions:
            return self.role_functions[role](index=index)

        return None

    def flags(self, index):
        flags = QAbstractItemModel.flags(self, index)

        if not index.isValid():
            return flags

        column = index.column()

        if self.editable_columns is not None:
            if self.editable_columns[column]:
                flags |= Qt.ItemIsEditable

        if self.checkbox_columns is not None:
            if self.checkbox_columns[column]:
                flags |= Qt.ItemIsUserCheckable

        return flags

    def index(self, row, column, parent):
        # TODO: commented out stuff ought to be good rather than
        #       breaking stuff.
        #
        #       http://stackoverflow.com/questions/26680168/pyqt-treeview-index-error-removing-last-row

        # if not self.hasIndex(row, column, parent):
        #     return QModelIndex()

        # if not parent.isValid():
        #     return QModelIndex()

        if row < 0 or column < 0:
            return QModelIndex()

        node = self.node_from_index(parent)
        child = node.child_at_row(row)

        if child is None:
            return QModelIndex()

        return self.createIndex(row, column, child)

    def columnCount(self, parent):
        return len(self.headers)

    def rowCount(self, parent):
        # TODO: this seems pretty particular to my present model
        #       "the second column should NOT have the same children
        #       as the first column in a row"
        #       https://github.com/bgr/PyQt5_modeltest/blob/62bc86edbad065097c4835ceb4eee5fa3754f527/modeltest.py#L222
        #
        #       then again, the Qt example does just this
        #       http://doc.qt.io/qt-5/qtwidgets-itemviews-simpletreemodel-example.html
        if parent.column() > 0:
            return 0

        node = self.node_from_index(parent)
        if node is None:
            return 0
        return len(node)

    def parent(self, child):
        if not child.isValid():
            return QModelIndex()

        node = self.node_from_index(child)

        if node is None:
            return QModelIndex()

        parent = node.tree_parent

        if parent in [None, self.root]:
            return QModelIndex()

        grandparent = parent.tree_parent
        if grandparent is None:
            return QModelIndex()
        row = grandparent.row_of_child(parent)

        if row == -1:
            raise Exception('row == -1')

        return self.createIndex(row, 0, parent)

    def node_from_index(self, index):
        if index.isValid():
            return index.internalPointer()
        else:
            return self.root

    def index_from_node(self, node):
        # TODO  make up another role for identification?
        if node in self.index_from_node_cache:
            index = self.index_from_node_cache[node]
        else:
            if node is self.root:
                index = QModelIndex()
            else:
                index = self.index(
                    row=node.tree_parent.row_of_child(node),
                    column=0,
                    parent=self.index_from_node(node.tree_parent)
                )

                self.index_from_node_cache[node] = index

        return index

    @pyqtSlot(TreeNode, int, TreeNode, int, list)
    def changed(self, start_node, start_column, end_node, end_column, roles):
        start_index = self.index_from_node(start_node)
        start_row = start_index.row()
        start_parent = start_index.parent()
        start_index = self.index(start_row, start_column, start_parent)
        if end_node is not start_node:
            end_index = self.index_from_node(end_node)
            end_row = end_index.row()
            end_parent = end_index.parent()
            end_index = self.index(end_row, end_column, end_parent)
        else:
            end_row = start_row
            end_parent = start_parent
            if end_column != start_column:
                end_index = self.index(end_row, end_column, end_parent)
            else:
                end_index = start_index

        self.dataChanged.emit(start_index, end_index, roles)

    @pyqtSlot(TreeNode, int, int)
    def begin_insert_rows(self, parent, start_row, end_row):
        self.beginInsertRows(self.index_from_node(parent), start_row, end_row)

    @pyqtSlot()
    def end_insert_rows(self):
        self.index_from_node_cache.clear()
        self.endInsertRows()

    @pyqtSlot(TreeNode, int, int)
    def begin_remove_rows(self, parent, start_row, end_row):
        self.beginRemoveRows(self.index_from_node(parent), start_row, end_row)

    @pyqtSlot()
    def end_remove_rows(self):
        self.index_from_node_cache.clear()
        self.endRemoveRows()

    @pyqtSlot()
    def set_root(self, root):
        self.beginResetModel()
        self.root = root
        self.endResetModel()
        self.root_changed.emit(root)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
