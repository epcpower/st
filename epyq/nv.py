#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
from epyq.abstractcolumns import AbstractColumns
import epyq.canneo
import json
import epyq.pyqabstractitemmodel
from epyq.treenode import TreeNode
from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot)
from PyQt5.QtWidgets import QFileDialog
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

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        multiplex_message, multiplex_value =\
            epyq.canneo.get_multiplex(self.matrix, msg)
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

    def to_dict(self):
        d = {}
        for child in self.children:
            d[child.fields.name] = child.get_human_value()

        return d

    def from_dict(self, d):
        for child in self.children:
            value = d.get(child.fields.name, None)
            if value is not None:
                child.set_human_value(value)


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


class NvModel(epyq.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, parent=None):
        editable_columns = Columns.fill(False)
        editable_columns.value = True

        epyq.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, editable_columns=editable_columns,
                parent=parent)

        self.headers = Columns(name='Name',
                               value='Value')

    def setData(self, index, data, role=None):
        if index.column() == Columns.indexes.value:
            if role == Qt.EditRole:
                node = self.node_from_index(index)
                try:
                    node.set_data(data)
                except ValueError:
                    return False
                self.dataChanged.emit(index, index)
                return True

        return False

    @pyqtSlot()
    def write_to_module(self):
        # TODO: device or module!?!?
        self.root.write_all_to_device()

    @pyqtSlot()
    def read_from_module(self):
        self.root.read_all_from_device()

    @pyqtSlot()
    def write_to_file(self):
        file_path = QFileDialog.getSaveFileName(
                filter='JSON (*.json);; All File (*)',
                initialFilter='JSON (*.json)')[0]
        if len(file_path) > 0:
            with open(file_path, 'w') as file:
                d = self.root.to_dict()
                s = json.dumps(d, sort_keys=True, indent=4)
                file.write(s)

    @pyqtSlot()
    def read_from_file(self):
        file_path = QFileDialog.getOpenFileName(
                filter='JSON (*.json);; All File (*)',
                initialFilter='JSON (*.json)')[0]
        if len(file_path) > 0:
            with open(file_path, 'r') as file:
                s = file.read()
                d = json.loads(s)
                self.root.from_dict(d)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
