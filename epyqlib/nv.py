#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
from epyqlib.abstractcolumns import AbstractColumns
import epyqlib.canneo
import epyqlib.twisted.busproxy
import epyqlib.twisted.nvs
import epyqlib.utils.twisted
import json
import epyqlib.pyqabstractitemmodel
from epyqlib.treenode import TreeNode
from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot)
from PyQt5.QtWidgets import QFileDialog
import time
import twisted.internet.defer
import twisted.internet.task

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(AbstractColumns):
    _members = ['name', 'value']

Columns.indexes = Columns.indexes()


class NoNv(Exception):
    pass


class NotFoundError(Exception):
    pass


class Nvs(TreeNode, epyqlib.canneo.QtCanListener):
    changed = pyqtSignal(TreeNode, int, TreeNode, int, list)
    set_status_string = pyqtSignal(str)

    def __init__(self, neo, bus, parent=None):
        TreeNode.__init__(self)
        epyqlib.canneo.QtCanListener.__init__(self, parent=parent)

        from twisted.internet import reactor
        self.protocol = epyqlib.twisted.nvs.Protocol()
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.protocol,
            reactor=reactor,
            bus=bus)

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
                       ['ReadParam_command', 'CommandSetNVParam_MUX']]
            for nv in signals:
                if nv.name not in ['SaveToEE_command']:
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

    def write_all_to_device(self, only_these=None):
        self.set_status_string.emit('Writing to device...')
        d = twisted.internet.defer.Deferred()
        d.callback(None)

        already_set_frames = set()

        def write_node(node, _=None):
            if node.frame not in already_set_frames:
                already_set_frames.add(node.frame)
                node.frame.update_from_signals()
                d.addCallback(lambda _: self.protocol.write(node))

        if only_these is None:
            self.traverse(call_this=write_node)
        else:
            for node in only_these:
                write_node(node=node)

        d.addCallback(epyqlib.utils.twisted.detour_result,
                      self.set_status_string.emit,
                      'Finished writing to device...')
        d.addErrback(epyqlib.utils.twisted.errbackhook)
        d.addErrback(epyqlib.utils.twisted.detour_result,
                     self.set_status_string.emit,
                     'Failed while writing to device...')

    def read_all_from_device(self, only_these=None):
        self.set_status_string.emit('Reading from device...')
        d = twisted.internet.defer.Deferred()
        d.callback(None)

        already_read_frames = set()

        from twisted.internet import reactor

        def read_node(node, _=None):
            if node.frame not in already_read_frames:
                already_read_frames.add(node.frame)
                node.frame.update_from_signals()

                d.addCallback(lambda _:
                              twisted.internet.task.deferLater(
                                  reactor, 0.02,
                                  self.protocol.read, node))

        if only_these is None:
            self.traverse(call_this=read_node)
        else:
            for node in only_these:
                read_node(node=node)

        d.addCallback(epyqlib.utils.twisted.detour_result,
                      self.set_status_string.emit,
                      'Finished reading from device...')
        d.addErrback(epyqlib.utils.twisted.errbackhook)
        d.addErrback(epyqlib.utils.twisted.detour_result,
                     self.set_status_string.emit,
                     'Failed while reading from device...')

    def all_changed(self):
        # TODO: CAMPid 99854759326728959578972453876695627489
        if len(self.children) > 0:
            self.changed.emit(
                self.children[0], Columns.indexes.value,
                self.children[-1], Columns.indexes.value,
                [Qt.DisplayRole])

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        multiplex_message, multiplex_value =\
            self.neo.get_multiplex(msg)

        if multiplex_message is None:
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

    def to_dict(self, include_secrets=False):
        d = {}
        for child in self.children:
            if include_secrets or not child.secret:
                d[child.fields.name] = child.get_human_value(for_file=True)

        return d

    def from_dict(self, d):
        only_in_file = list(d.keys())

        for child in self.children:
            value = d.get(child.fields.name, None)
            if value is not None:
                child.set_human_value(value)
                only_in_file.remove(child.fields.name)
            else:
                print("Nv value named '{}' not found when loading from dict"
                      .format(child.fields.name))

        for name in only_in_file:
            print("Unrecognized NV value named '{}' found when loading "
                  "from dict".format(name))

    def module_to_nv(self):
        self.set_status_string.emit('Requested save to NV...')
        self.save_signal.set_value(self.save_value)
        self.save_frame.update_from_signals()
        d = self.protocol.write(self.save_signal)
        d.addCallback(self._module_to_nv_response)
        d.addErrback(epyqlib.utils.twisted.errbackhook)

    def _module_to_nv_response(self, result):
        if result == 1:
            feedback = 'Save to NV confirmed'
        else:
            feedback = 'Save to NV failed ({})'.format(
                self.confirm_save_signal.full_string
            )

        self.set_status_string.emit(feedback)

    def logger_set_frames(self):
        frames = [frame for frame in self.set_frames.values()
                  if frame.mux_name.startswith('LoggerChunk')]
        frames.sort(key=lambda frame: frame.mux_name)

        return frames

    def signal_from_names(self, frame_name, value_name):
        frame = [f for f in self.set_frames.values()
                 if f.mux_name == frame_name]

        try:
            frame, = frame
        except ValueError as e:
            raise NotFoundError(
                'Frame not found: {}'.format(frame_name)) from e

        signal = [s for s in frame.signals
                   if s.name == value_name]

        try:
            signal, = signal
        except ValueError as e:
            raise NotFoundError(
                'Signal not found: {}'.format(signal_name)) from e

        return signal


class Nv(epyqlib.canneo.Signal, TreeNode):
    def __init__(self, signal, frame, parent=None):
        epyqlib.canneo.Signal.__init__(self, signal=signal, frame=frame,
                                    parent=parent)
        TreeNode.__init__(self)

        self.fields = Columns(name='{}:{}'.format(self.frame.mux_name,
                                                  self.name),
                              value='')
        self.clear()

    def set_value(self, value, force=False, check_range=False):
        epyqlib.canneo.Signal.set_value(self,
                                        value=value,
                                        force=force,
                                        check_range=check_range)
        self.fields.value = self.full_string

    def set_data(self, data):
        # self.fields.value = value
        self.set_human_value(data)

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


class Frame(epyqlib.canneo.Frame, TreeNode):
    def __init__(self, message=None, tx=False, frame=None,
                 multiplex_value=None, signal_class=Nv,
                 parent=None):
        epyqlib.canneo.Frame.__init__(self, frame=frame,
                                   multiplex_value=multiplex_value,
                                   signal_class=signal_class,
                                   parent=parent)
        TreeNode.__init__(self, parent)

        for signal in self.signals:
            if signal.name == "ReadParam_command":
                self.read_write = signal
                break

    def update_from_signals(self, for_read=False, function=None):
        epyqlib.canneo.Frame.update_from_signals(self, function=function)


def ufs(signal):
    if signal.name in ['ReadParam_command', 'CommandSetNVParam_MUX']:
        return signal.value
    else:
        # TODO: CAMPid 9395616283654658598648263423685
        # TODO: and _offset...

        scaled_value = (signal.min - signal.offset) / signal.factor
        return scaled_value


class NvModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    set_status_string = pyqtSignal(str)

    def __init__(self, root, parent=None):
        editable_columns = Columns.fill(False)
        editable_columns.value = True

        epyqlib.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
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
    def write_to_file(self, parent=None):
        filters = [
            ('EPC Parameters', ['epp']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(
            filters, save=True, parent=parent)

        if filename is None:
            return

        if len(filename) > 0:
            with open(filename, 'w') as file:
                d = self.root.to_dict()
                s = json.dumps(d, sort_keys=True, indent=4)
                file.write(s)

                self.set_status_string.emit(
                    'Saved to "{}"'.format(filename)
                )

    @pyqtSlot()
    def read_from_file(self, parent=None):
        filters = [
            ('EPC Parameters', ['epp']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(filters, parent=parent)

        if filename is None:
            return

        if len(filename) > 0:
            with open(filename, 'r') as file:
                s = file.read()
                d = json.loads(s)
                self.root.from_dict(d)

                self.set_status_string.emit(
                    'Loaded from "{}"'.format(filename)
                )


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
