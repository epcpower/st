#!/usr/bin/env python3

#TODO: """DocString if there is one"""

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class TreeNode:
    def __init__(self,  tx=False, parent=None):
        self.last = None

        self.tx = tx

        self.tree_parent = None
        self.set_parent(parent)
        self.children = []

    def set_parent(self, parent):
        self.tree_parent = parent
        if self.tree_parent is not None:
            self.tree_parent.append_child(self)

    def append_child(self, child):
        self.children.append(child)
        child.tree_parent = self

    def child_at_row(self, row):
        try:
            return self.children[row]
        except IndexError:
            return None

    def row_of_child(self, child):
        for i, item in enumerate(self.children):
            if item == child:
                return i
        return -1

    def remove_child(self, row=None, child=None):
        if child is None:
            child = self.children[row]

        self.children.remove(child)

        return True

    def traverse(self, call_this, payload=None):
        for child in self.children:
            if len(child.children) == 0:
                call_this(child, payload)
            else:
                child.traverse(child, call_this, payload)

    def __len__(self):
        return len(self.children)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
