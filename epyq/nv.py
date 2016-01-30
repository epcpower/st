#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
from epyq.abstractcolumns import AbstractColumns
import epyq.canneo
from epyq.treenode import TreeNode
from PyQt5.QtCore import (Qt, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSignal, pyqtSlot)
import time

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(AbstractColumns):
    _members = ['name', 'value']

Columns.indexes = Columns.indexes()


class Nvs(TreeNode, epyq.canneo.QtCanListener):
    changed = pyqtSignal(TreeNode, int, TreeNode, int, list)

    def __init__(self, matrix, bus, parent=None):
        TreeNode.__init__(self)
        epyq.canneo.QtCanListener.__init__(self, parent=parent)

        self.bus = bus
        self.matrix = matrix
        self.message_received_signal.connect(self.message_received)

        self.set_frames = [f for f in self.matrix._fl._list
                       if f._name == 'CommandSetNVParam'][0].multiplex_frames
        self.status_frames = [f for f in self.matrix._fl._list
                       if f._name == 'StatusNVParam'][0].multiplex_frames
        for value, frame in self.set_frames.items():
            signals = [s.signal for s in frame._signals
                       if 'signal' in s.__dict__]
            signals = [s for s in signals if s.signal._multiplex is not 'Multiplexor']
            signals = [s for s in signals if s.signal._name not in
                       ['SaveToEE_command', 'ReadParam_command']]
            for nv in signals:
                nv.frame.send.connect(self.send)
                self.append_child(nv)
                nv.frame.status_frame = self.status_frames[value]
                self.status_frames[value].set_frame = nv.frame

    def names(self):
        return '\n'.join([n.fields.name for n in self.children])

    def write_all_to_device(self):
        self.traverse(lambda node: node.write_to_device())

    def read_all_from_device(self):
        self.traverse(lambda node: node.read_from_device())

    @pyqtSlot(can.Message)
    def send(self, message):
        self.bus.send(message)
        time.sleep(0.01)

    # TODO: campy 975489957269239475565893294237
    def get_multiplex(self, message):
        base_frame = self.matrix.frameById(message.arbitration_id)
        try:
            frame = base_frame.multiplex_frame
        except AttributeError:
            frame = base_frame
            multiplex_value = None
        else:
            # finish the multiplex thing
            frame.frame.unpack(message.data)
            multiplex_value = base_frame.multiplex_signal.signal.value
            # TODO: stop using strings for integers...
            frame = base_frame.multiplex_frames[str(multiplex_value)]

        return (frame, multiplex_value)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        multiplex_message, multiplex_value = self.get_multiplex(msg)
        if multiplex_value is not None and multiplex_message in self.status_frames.values():
            multiplex_message.frame.unpack(msg.data)
            # multiplex_message.frame.update_canneo_from_matrix_signals()

            status_signals = [s.signal for s in multiplex_message._signals]
            sort_key = lambda s: s.signal._startbit
            status_signals.sort(key=sort_key)
            set_signals = [s.signal for s
                           in multiplex_message.set_frame.frame._signals]
            set_signals.sort(key=sort_key)
            for status, set in zip(status_signals, set_signals):
                set.set_value(status.value)

            for child in self.children:
                if child in set_signals:
                    self.changed.emit(
                        child, Columns.indexes.value,
                        child, Columns.indexes.value,
                        [Qt.DisplayRole])

    def unique(self):
        # TODO: actually identify the object
        return '-'


class Frame(epyq.canneo.Frame, TreeNode):
    def __init__(self, message=None, tx=False, frame=None, parent=None):
        epyq.canneo.Frame.__init__(self, frame=frame, parent=parent)
        TreeNode.__init__(self, parent)

        try:
            for signal in self.frame._signals:
                self.append_child(Nv(signal, frame=self))
        except KeyError:
            pass

        for child in self.children:
            if child.signal._name == "ReadParam_command":
                self.read_write = child
                break

    def send_write(self):
        try:
            read_write = self.read_write
        except AttributeError:
            pass
        else:
            # TODO: magic number
            read_write.set_data(0)

        self.update_from_signals()
        self._send()

    def send_read(self):
        try:
            read_write = self.read_write
        except AttributeError:
            # TODO: custom exception? push the skipping to callee?
            pass
        else:
            # TODO: magic number
            read_write.set_data(1)
            self.update_from_signals()
            self._send()

    def update_from_signals(self):
        epyq.canneo.Frame.update_from_signals(self)


class Nv(epyq.canneo.Signal, TreeNode):
    def __init__(self, signal, frame, parent=None):
        epyq.canneo.Signal.__init__(self, signal=signal, frame=frame,
                                    parent=parent)
        TreeNode.__init__(self)

        self.fields = Columns(name=signal._name,
                              value='-')

    # TODO: campy 909457829293754985498
    def set_value(self, value):
        epyq.canneo.Signal.set_value(self, value)
        self.fields.value = self.full_string

    def set_data(self, data):
        # self.fields.value = value
        self.set_human_value(data)

    def write_to_device(self):
        # TODO: this is going to be repetitive since there are multiple
        #       values in many of the frames
        self.frame.send_write()

    def read_from_device(self):
        # TODO: this is going to be repetitive since there are multiple
        #       values in many of the frames
        self.frame.send_read()
        # TODO: then we'll have to receive them too...

    def unique(self):
        # TODO: make it more unique
        return str(self.fields.name) + '__'


# pretty campy 0958709927126785496723750
class NvModel(QAbstractItemModel):
    # TODO: seems like a lot of boilerplate which could be put in an abstract class
    #       (wrapping the abstract class?  hmmm)

    def __init__(self, root, parent=None):
        QAbstractItemModel.__init__(self, parent=parent)

        self.root = root
        self.headers = Columns(name='Name',
                               value='Value')

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

    def flags(self, index):
        flags = QAbstractItemModel.flags(self, index)

        if index.column() == Columns.indexes.value:
            flags |= Qt.ItemIsEditable

        return flags

    def setData(self, index, data, role=None):
        if index.column() == Columns.indexes.value:
            if role == Qt.EditRole:
                node = self.node_from_index(index)
                node.set_data(data)
                self.dataChanged.emit(index, index)
                return True

        return False

    def index(self, row, column, parent):
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))
        # if not parent.isValid():
        #     parent_item = self.root
        # else:
        #     parent_item = parent.internalPointer()
        #
        # child_item = parent_item.children[row]
        # if child_item:
        #     return self.createIndex(row, column, child_item)
        # else:
        #     return QModelIndex()

    def data(self, index, role):
        if role == Qt.DecorationRole:
            return QVariant()

        if role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignTop | Qt.AlignLeft))

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
            if index.column() == Columns.indexes.value:
                try:
                    value = node.get_human_value()
                except TypeError:
                    value = ''
            else:
                value = node.fields[index.column()]

            # TODO: totally dt specific
            if isinstance(value, float):
                value = str(value)

            return QVariant(value)

        return QVariant()

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

    @pyqtSlot()
    def write_to_module(self):
        # TODO: device or module!?!?
        self.root.write_all_to_device()

    @pyqtSlot()
    def read_from_module(self):
        self.root.read_all_from_device()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
