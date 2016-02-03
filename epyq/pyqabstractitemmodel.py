#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from epyq.treenode import TreeNode
from PyQt5.QtCore import (Qt, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSlot)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class PyQAbstractItemModel(QAbstractItemModel):
    def __init__(self, root, parent=None):
        QAbstractItemModel.__init__(self, parent=parent)

        self.root = root

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

    def flags(self, index):
        return QAbstractItemModel.flags(self, index)

    def index(self, row, column, parent):
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))

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
            return node.index
        except AttributeError:
            node.index = self.match(self.index(0, len(self.headers), QModelIndex()),
                                    Qt.DisplayRole,
                                    node.unique(),
                                    1,
                                    Qt.MatchRecursive)[0]

        return node.index

    @pyqtSlot(TreeNode, int, TreeNode, int, list)
    def changed(self, start_node, start_column, end_node, end_column, roles):
        start_index = self.index_from_node(start_node)
        start_index = self.index(start_index.row(), start_column, start_index.parent())
        if end_node is not start_node:
            end_index = self.index_from_node(end_node)
            end_index = self.index(end_index.row(), end_column, end_index.parent())
        else:
            end_index = start_index
        self.dataChanged.emit(start_index, end_index, roles)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
