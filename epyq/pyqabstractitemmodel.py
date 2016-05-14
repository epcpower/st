#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from epyq.treenode import TreeNode
from PyQt5.QtCore import (Qt, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSlot)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class PyQAbstractItemModel(QAbstractItemModel):
    def __init__(self, root, checkbox_columns=None, editable_columns=None,
                 parent=None):
        QAbstractItemModel.__init__(self, parent=parent)

        self.root = root
        self.checkbox_columns = checkbox_columns
        self.editable_columns = editable_columns

        self.index_from_node_cache = {}

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

    def data(self, index, role):
        if role == Qt.DecorationRole:
            return QVariant()

        if role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignTop | Qt.AlignLeft))

        if role == Qt.CheckStateRole:
            if self.checkbox_columns is not None:
                if self.checkbox_columns[index.column()]:
                    node = self.node_from_index(index)
                    try:
                        return node.checked(index.column())
                    except AttributeError:
                        return QVariant()

        if role == Qt.DisplayRole:
            node = self.node_from_index(index)

            if index.column() == len(self.headers):
                return QVariant(node.unique())
            else:
                try:
                    return QVariant(node.fields[index.column()])
                except IndexError:
                    return QVariant()

        if role == Qt.EditRole:
            node = self.node_from_index(index)
            try:
                get = node.get_human_value
            except AttributeError:
                value = node.fields[index.column()]
            else:
                try:
                    value = get()
                except TypeError:
                    value = ''

            if value is None:
                value = ''
            else:
                value = str(value)

            return QVariant(value)

        return QVariant()

    def flags(self, index):
        flags = QAbstractItemModel.flags(self, index)

        if self.editable_columns is not None:
            if self.editable_columns[index.column()]:
                flags |= Qt.ItemIsEditable

        if self.checkbox_columns is not None:
            if self.checkbox_columns[index.column()]:
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

        node = self.node_from_index(parent)
        child = node.child_at_row(row)

        # if child is None:
        #     return QModelIndex()

        return self.createIndex(row, column, child)

    def columnCount(self, parent):
        return len(self.headers)

    def rowCount(self, parent):
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

        if parent is None:
            return QModelIndex()

        grandparent = parent.tree_parent
        if grandparent is None:
            return QModelIndex()
        row = grandparent.row_of_child(parent)

        assert row != - 1
        return self.createIndex(row, 0, parent)

    def node_from_index(self, index):
        if index.isValid():
            return index.internalPointer()
        else:
            return self.root

    def index_from_node(self, node):
        # TODO  make up another role for identification?
        try:
            index = self.index_from_node_cache[node]
        except KeyError:
            if node is self.root:
                index = QModelIndex()
            else:
                index = self.match(self.index(0, len(self.headers), QModelIndex()),
                                   Qt.DisplayRole,
                                   node.unique(),
                                   1,
                                   Qt.MatchRecursive)[0]

                self.index_from_node_cache[node] = index

        return index

    @pyqtSlot(TreeNode, int, TreeNode, int, list)
    def changed(self, start_node, start_column, end_node, end_column, roles):
        start_index = self.index_from_node(start_node)
        start_index = self.index(start_index.row(), start_column, start_index.parent())
        if end_node is not start_node:
            end_index = self.index_from_node(end_node)
            end_index = self.index(end_index.row(), end_column, end_index.parent())
        else:
            end_index = start_index

        if (end_node is not start_node) or (end_column != start_column):
            end_index = self.index(end_index.row(), end_column, end_index.parent())


        self.dataChanged.emit(start_index, end_index, roles)

    @pyqtSlot(TreeNode, int, int)
    def begin_insert_rows(self, parent, start_row, end_row):
        self.beginInsertRows(self.index_from_node(parent), start_row, end_row)

    @pyqtSlot()
    def end_insert_rows(self):
        self.index_from_node_cache = {}
        self.endInsertRows()

    @pyqtSlot(TreeNode, int, int)
    def begin_remove_rows(self, parent, start_row, end_row):
        self.beginRemoveRows(self.index_from_node(parent), start_row, end_row)

    @pyqtSlot()
    def end_remove_rows(self):
        self.index_from_node_cache = {}
        self.endRemoveRows()

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
