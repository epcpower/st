#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
from collections import OrderedDict
from epyq.abstractcolumns import AbstractColumns
import epyq.canneo
import functools
import json
import epyq.pyqabstractitemmodel
from epyq.treenode import TreeNode
from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSlot, QTimer)
from PyQt5.QtWidgets import QFileDialog
import time

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(AbstractColumns):
    _members = ['name', 'action']

Columns.indexes = Columns.indexes()


class Node(TreeNode):
    def __init__(self, text, action=None):
        TreeNode.__init__(self)

        self.fields = Columns(name=text,
                              action=None)

    # def to_ordered_dict(self):
    #     d = OrderedDict()
    #     for child in self.children:
    #         # TODO: actually store the action not its string
    #         d[child.fields.name] = child.fields.action
    #
    #     return d

    def from_ordered_dict(self, d):
        for child in self.children:
            value = d.get(child.fields.name, None)
            if value is not None:
                child.set_human_value(value)


class ListMenuModel(epyq.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, parent=None):
        epyq.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, alignment=Qt.AlignVCenter | Qt.AlignLeft,
                parent=parent)

        self.headers = Columns(name='Name',
                               action='Action')

        self.set_root(root)

    @pyqtSlot(Node)
    def node_clicked(self, node):
        QTimer.singleShot(100,
                          functools.partial(
                              self.set_root,
                              node
                          ))

    @pyqtSlot(bool)
    def esc_clicked(self, _):
        new_root = self.root.tree_parent
        if new_root is not None:
            self.node_clicked(new_root)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
