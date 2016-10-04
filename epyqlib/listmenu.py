#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
from collections import OrderedDict
from epyqlib.abstractcolumns import AbstractColumns
import epyqlib.canneo
import functools
import json
import epyqlib.pyqabstractitemmodel
from epyqlib.treenode import TreeNode
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
                              action=action)

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

    def find_child(self, value):
        for child in self.children:
            if child.fields.name == value or child.fields.action == value:
                return child

    @property
    def action(self):
        return self.fields.action

    @action.setter
    def action(self, action):
        self.fields.action = action

    def unique(self):
        return self

class ListMenuModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, parent=None):
        epyqlib.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, alignment=Qt.AlignVCenter | Qt.AlignLeft,
                parent=parent)

        self.headers = Columns(name='Name',
                               action='Action')

        self.set_root(root)

    @pyqtSlot(Node)
    def node_clicked(self, node):
        if node.fields.action is None:
            action = functools.partial(
                self.set_root,
                node
            )
        else:
            action = node.fields.action

        QTimer.singleShot(100, action)

    @pyqtSlot(bool)
    def esc_clicked(self, _):
        new_root = self.root.tree_parent
        if new_root is not None:
            self.node_clicked(new_root)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
