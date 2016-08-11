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


class NoNv(Exception):
    pass


class Nvs(TreeNode, epyq.canneo.QtCanListener):
    changed = pyqtSignal(TreeNode, int, TreeNode, int, list)
    set_status_string = pyqtSignal(str)

    def __init__(self, neo, bus, parent=None):
        TreeNode.__init__(self)
        epyq.canneo.QtCanListener.__init__(self, parent=parent)

        self.bus = bus
        self.neo = neo
        self.message_received_signal.connect(self.message_received)


        self.set_frames = [f for f in self.neo.frames
                       if f.name == 'CommandSetNVParam']
        try:
            self.set_frames = self.set_frames[0]
        except IndexError:
            # TODO: custom error
            raise NoNv()

        self.set_frames = self.set_frames.multiplex_frames
        self.status_frames = [f for f in self.neo.frames
                       if f.name == 'StatusNVParam'][0].multiplex_frames

        self.save_frame = None
        self.save_signal = None
        self.save_value = None
        self.confirm_save_frame = None
        self.confirm_save_multiplex_value = None
        self.confirm_save_signal = None
        self.confirm_save_value = None
        for frame in self.set_frames.values():
            for signal in frame.signals:
                if signal.name == 'SaveToEE_command':
                    for key, value in signal.enumeration.items():
                        if value == 'Enable':
                            self.save_frame = frame
                            self.save_signal = signal
                            self.save_value = float(key)

        save_status_name = 'SaveToEE_status'
        for frame in self.status_frames.values():
            for signal in frame.signals:
                if signal.name == save_status_name:
                    for key, value in signal.enumeration.items():
                        if value == 'Enable':
                            self.confirm_save_frame = frame
                            self.confirm_save_multiplex_value = signal.multiplex
                            self.confirm_save_signal = signal
                            self.confirm_save_value = float(key)

        if self.confirm_save_frame is None:
            raise Exception(
                "'{}' signal not found in NV parameter interface".format(
                    save_status_name
                ))

        # TODO: kind of an ugly manual way to connect this
        self.status_frames[0].set_frame = self.set_frames[0]
        for value, frame in self.set_frames.items():
            signals = [s for s in frame.signals]
            signals = [s for s in signals if s.multiplex is not 'Multiplexor']
            signals = [s for s in signals if s.name not in
                       ['SaveToEE_command', 'ReadParam_command',
                        'CommandSetNVParam_MUX']]
            frame.send.connect(self.send)
            for nv in signals:
                self.append_child(nv)

                nv.frame.status_frame = self.status_frames[value]
                self.status_frames[value].set_frame = nv.frame

                nv.status_signal = [s for s in self.status_frames[value].signals if s.start_bit == nv.start_bit][0]
                nv.status_signal.set_signal = nv

        # TODO: this should probably be done in the view but this is easier for now
        self.children.sort(key=lambda c: (c.frame.mux_name, c.name))

        duplicate_names = set()
        found_names = set()
        for child in self.children:
            name = child.fields.name
            if name not in found_names:
                found_names.add(name)
            else:
                duplicate_names.add(name)

        if len(duplicate_names) > 0:
            raise Exception('Duplicate NV parameter names found: {}'.format(
                ', '.join(duplicate_names)))

    def names(self):
        return '\n'.join([n.fields.name for n in self.children])

    def write_all_to_device(self):
        self.set_status_string.emit('Writing to device...')
        self.traverse(
            call_this=lambda node, batch_set: node.write_to_device(batch_set),
            payload=set())
        self.set_status_string.emit('Finished writing to device...')

    def read_all_from_device(self):
        self.set_status_string.emit('Reading from device...')
        self.traverse(
            call_this=lambda node, batch_set: node.read_from_device(batch_set),
            payload=set())
        self.all_changed()
        self.set_status_string.emit('Finished reading from device...')

    def all_changed(self):
        # TODO: CAMPid 99854759326728959578972453876695627489
        if len(self.children) > 0:
            self.changed.emit(
                self.children[0], Columns.indexes.value,
                self.children[-1], Columns.indexes.value,
                [Qt.DisplayRole])

    @pyqtSlot(can.Message)
    def send(self, message):
        self.bus.send(message)
        time.sleep(0.02)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        multiplex_message, multiplex_value =\
            self.neo.get_multiplex(msg)

        if multiplex_message is None:
            return

        if multiplex_message is self.confirm_save_frame:
            if multiplex_value is self.confirm_save_multiplex_value:
                # TODO: might be unnecessary since same frame as
                #       unpacked for multiplex info
                self.confirm_save_frame.unpack(msg.data)

                status = self.confirm_save_signal.value

                if status == 1:
                    feedback = 'Save to NV confirmed'
                else:
                    feedback = 'Save to NV failed ({})'.format(
                        self.confirm_save_signal.full_string
                    )

                self.set_status_string.emit(feedback)

                return

        if multiplex_value is not None and multiplex_message in self.status_frames.values():
            multiplex_message.unpack(msg.data)
            # multiplex_message.frame.update_canneo_from_matrix_signals()

            status_signals = multiplex_message.signals
            sort_key = lambda s: s.start_bit
            status_signals.sort(key=sort_key)
            set_signals = multiplex_message.set_frame.signals
            set_signals.sort(key=sort_key)
            for status, set in zip(status_signals, set_signals):
                set.set_value(status.value)

            self.all_changed()

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

    def module_to_nv(self):
        self.set_status_string.emit('Requested save to NV...')
        self.save_signal.set_value(self.save_value)
        self.save_frame.update_from_signals()
        self.send(self.save_frame.to_message())
        # TODO: is there a response from device to confirm?


class Nv(epyq.canneo.Signal, TreeNode):
    def __init__(self, signal, frame, parent=None):
        epyq.canneo.Signal.__init__(self, signal=signal, frame=frame,
                                    parent=parent)
        TreeNode.__init__(self)

        self.fields = Columns(name=signal._name,
                              value='')
        self.clear()

    def set_value(self, value):
        epyq.canneo.Signal.set_value(self, value)
        self.fields.value = self.full_string

    def set_data(self, data):
        # self.fields.value = value
        self.set_human_value(data)

    def write_to_device(self, batch_set=None):
        if batch_set is None:
            batch_set = set()
        # TODO: this is going to be repetitive since there are multiple
        #       values in many of the frames
        frame = self.frame
        if frame not in batch_set:
            frame.send_write()
            batch_set.add(frame)

    def read_from_device(self, batch_set=None):
        if batch_set is None:
            batch_set = set()
        # TODO: this is going to be repetitive since there are multiple
        #       values in many of the frames
        frame = self.frame
        self.clear()
        if frame not in batch_set:
            frame.send_read()
            batch_set.add(frame)
        # TODO: then we'll have to receive them too...

    def clear(self):
        self.set_value(float('nan'))
        try:
            status_signal = self.status_signal
        except AttributeError:
            pass
        else:
            status_signal.set_value(float('nan'))

    def unique(self):
        # TODO: make it more unique
        return str(self.fields.name) + '__'


class Frame(epyq.canneo.Frame, TreeNode):
    def __init__(self, message=None, tx=False, frame=None,
                 multiplex_value=None, signal_class=Nv,
                 parent=None):
        epyq.canneo.Frame.__init__(self, frame=frame,
                                   multiplex_value=multiplex_value,
                                   signal_class=signal_class,
                                   parent=parent)
        TreeNode.__init__(self, parent)

        for signal in self.signals:
            self.append_child(signal)

        for child in self.children:
            if child.name == "ReadParam_command":
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
            self.update_from_signals(function=ufs)
            self._send()

    def update_from_signals(self, for_read=False, function=None):
        epyq.canneo.Frame.update_from_signals(self, function=function)


def ufs(signal):
    if signal.name in ['ReadParam_command', 'CommandSetNVParam_MUX']:
        return signal.value
    else:
        # TODO: CAMPid 9395616283654658598648263423685
        # TODO: and _offset...

        scaled_value = (signal.min - signal.offset) / signal.factor
        return scaled_value


class NvModel(epyq.pyqabstractitemmodel.PyQAbstractItemModel):
    set_status_string = pyqtSignal(str)

    def __init__(self, root, parent=None):
        editable_columns = Columns.fill(False)
        editable_columns.value = True

        epyq.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, editable_columns=editable_columns,
                parent=parent)

        self.headers = Columns(name='Name',
                               value='Value')

        root.set_status_string.connect(self.set_status_string)

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
    def module_to_nv(self):
        # TODO: monitor and report success/failure of write
        self.root.module_to_nv()

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

                self.set_status_string.emit(
                    'Saved to "{}"'.format(file_path)
                )

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

                self.set_status_string.emit(
                    'Loaded from "{}"'.format(file_path)
                )


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
