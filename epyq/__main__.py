#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import sys
# sys.path.append('../canmatrix')

import bitstruct
import can
import copy
import math
import platform
import threading
import time

import canmatrix.importany as importany
import canmatrix.canmatrix as canmatrix

from PyQt5.QtCore import (Qt, QObject, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSignal, pyqtSlot)


class Signal(QObject):
    _my_signal = pyqtSignal(int)

    def __init__(self, signal, frame, connect=None, parent=None):
        signal.signal = self
        self.signal = signal
        # TODO: what about QObject parameters
        QObject.__init__(self, parent=parent)
        self.value = None

        self.frame = frame

        if connect is not None:
            self.connect(connect)

    def connect(self, target):
        self._my_signal.connect(target)

    def set_value(self, value):
        value = copy.deepcopy(value)
        self.value = value
        self._my_signal.emit(value)


class QtCanListener(QObject, can.Listener):
    message_received_signal = pyqtSignal(can.Message)

    def __init__(self, receiver=None, parent=None):
        QObject.__init__(self, parent=parent)
        can.Listener.__init__(self)

        if receiver is not None:
            self.receiver(receiver)

    def receiver(self, slot):
        self.message_received_signal.connect(slot)

    def on_message_received(self, msg):
        # TODO: Be careful since this is no longer being deep copied.
        #       It seems safe based on looking at the socketcan and
        #       pcan bus objects that construct a new Message() for
        #       each one received.  The Notifier loop just forgets
        #       about the message as soon as it is sent here.
        #
        #       This optimization is being justified by the 25% drop
        #       in CPU usage.

        self.message_received_signal.emit(msg)


class Frame(QtCanListener):
    send = pyqtSignal(can.Message)

    def __init__(self, frame, parent=None):
        QtCanListener.__init__(self, self.message_received, parent=parent)

        frame.frame = self
        self.frame = frame

    def unpad(self):
        self.frame._signals = [s for s in self.frame._signals
                               if s._name != '__padding__']

    def pad(self):
        self.unpad()
        # TODO: use getMsbStartbit() if intel/little endian
        #       and search for all other uses
        self.frame._signals.sort(key=lambda x: x.getMsbReverseStartbit())
        Pad = lambda start_bit, length: canmatrix.Signal(name='__padding__',
                                                         startbit=start_bit,
                                                         signalsize=length,
                                                         byteorder=0,
                                                         valuetype=None,
                                                         factor=None,
                                                         offset=None,
                                                         min=None,
                                                         max=None,
                                                         unit=None,
                                                         reciever=None,
                                                         multiplex=None)
        # TODO: 1 or 0, which is the first bit per canmatrix?
        bit = 0
        # pad for unused bits
        padded_signals = []
        for signal in self.frame._signals:
            startbit = signal.getMsbReverseStartbit()
            if startbit < bit:
                raise Exception('too far ahead!')
            padding = startbit - bit
            if padding:
                pad = Pad(bit, padding)
                padded_signals.append(pad)
                bit += pad._signalsize
            padded_signals.append(signal)
            bit += signal._signalsize
        # TODO: 1 or 0, which is the first bit per canmatrix?
        padding = (self.frame._Size * 8) - bit
        if padding < 0:
            # TODO: fix the common issue so the exception can be used
            # raise Exception('frame too long!')
            print('Frame too long!  (but this is expected for now since the DBC seems wrong)')
        elif padding > 0:
            padded_signals.append(Pad(bit, padding))

        self.frame._signals = padded_signals

    def format(self):
        # None is for handling padding
        types = {None: 'u', '+': 'u', '-': 's'}
        order = {None: '<', 0: '>', 1: '<'}

        fmt = ['{}{}{}'.format(order[s._byteorder], types[s._valuetype], s._signalsize)
               for s in self.frame._signals]
        return ''.join(fmt)

    def pack(self, data):
        self.pad()

        if data == self:
            data = []
            for signal in self.frame._signals:
                try:
                    value = signal.signal.value
                except:
                    value = 0

                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = 0
                data.append(value)

        return bitstruct.pack(self.format(), *data)

    def unpack(self, data):
        rx_length = len(data)
        if rx_length != self.frame._Size:
            print('Received message length {rx_length} != {self.frame._Size} received'.format(**locals()))
        else:
            self.pad()

            # TODO: endianness for bigger signals
            # bits required 2**math.ceil(math.log2(x))
            unpacked = bitstruct.unpack(self.format(), data)
            for s, v in zip(self.frame._signals, unpacked):
                try:
                    s.signal.set_value(v)
                except AttributeError:
                    pass

    def update_from_signals(self):
        # TODO: actually do this
        self.data = self.pack(self)
        # TODO: isn't this very MessageNode'y rather than Frame'y?
        # TODO: quit repeating (98476589238759)
        self.fields.value = ' '.join(['{:02X}'.format(byte) for byte in self.data])
        self.send.emit(can.Message(extended_id=self.frame._extended,
                                   arbitration_id=self.frame._Id,
                                   dlc=self.frame._Size,
                                   data=self.data))

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if msg.arbitration_id == self.frame._Id and msg.id_type == self.frame._extended:
            self.unpack(msg.data)


from PyQt5 import QtCore, QtWidgets, QtGui, uic
import os
class Window(QtWidgets.QMainWindow):
    def __init__(self, matrix, tx_model, rx_model, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'main.ui')
        self.ui = uic.loadUi(ui_file, self)

        # TODO: CAMPy
        self.ui.tx.setModel(tx_model)
        self.ui.tx.header().setStretchLastSection(False)
        for i in TxRxColumns.indexes:
            self.ui.tx.header().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)
        # TODO: would be nice to share between message and signal perhaps?
        self.ui.tx.header().setSectionResizeMode(TxRxColumns.indexes.message, QtWidgets.QHeaderView.Stretch)
        self.ui.rx.setModel(rx_model)
        self.ui.rx.header().setStretchLastSection(False)
        do_not_resize = [TxRxColumns.indexes.value, TxRxColumns.indexes.dt]
        for i in [i for i in TxRxColumns.indexes if i not in do_not_resize]:
            self.ui.rx.header().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)
        # TODO: would be nice to share between message and signal perhaps?
        self.ui.rx.header().setSectionResizeMode(TxRxColumns.indexes.message, QtWidgets.QHeaderView.Stretch)

        children = self.findChildren(QtCore.QObject)
        targets = [c for c in children if
                   c.property('frame') and c.property('signal')]

        for target in targets:
            frame_name = target.property('frame')
            signal_name = target.property('signal')

            frame = matrix.frameByName(frame_name).frame
            signal = frame.frame.signalByName(signal_name).signal
            # TODO: get the frame into the signal constructor where it's called now
            # signal = Signal(frame.frame.signalByName(signal_name), frame)

            breakpoints = [75, 90]
            colors = [QtCore.Qt.darkGreen, QtCore.Qt.darkYellow, QtCore.Qt.darkRed]

            try:
                target.setColorRanges(colors, breakpoints)
            except AttributeError:
                pass

            signal.connect(target.setValue)
            target.setRange(0, 100)#signal._min, signal._max)


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
        return self.children[row]

    def row_of_child(self, child):
        for i, item in enumerate(self.children):
            if item == child:
                return i
        return -1

    def remove_child(self, row):
        value = self.children[row]
        self.children.remove(value)

        return True

    def __len__(self):
        return len(self.children)


class MessageNode(Frame, TreeNode):
    def __init__(self, message, tx=False, frame=None, parent=None):
        Frame.__init__(self, frame=frame, parent=parent)
        TreeNode.__init__(self, parent)

        self.fields = TxRxColumns.none()
        self.last_time = None

        self.tx = tx

        try:
            for signal in self.frame._signals:
                self.append_child(SignalNode(signal, frame=self, tx=self.tx))
        except KeyError:
            pass

        # TODO: quit doing this frame->fields in two places (098098234709572943)
        format = '0x{{:0{}X}}'
        if frame._extended:
            format = format.format(8)
        else:
            format = format.format(3)

        self.fields = TxRxColumns(id=format.format(self.frame._Id),
                                  message=self.frame._name,
                                  signal='',
                                  length='{} B'.format(self.frame._Size),
                                  value='-',
                                  dt=None)

        if message is not None:
            self.extract_message(message)

    def extract_message(self, message, verify=True):
        # TODO: stop calling this from txrx and use the standard Frame reception

        if verify:
            # TODO: make sure the message matches the id/type and length
            pass

        # TODO: I think this is not needed
        # self.message = message

        # TODO: quit doing this frame->fields in two places (098098234709572943)
        # TODO: should this formatting be done in the other place?
        format = '0x{{:0{}X}}'
        if message.id_type:
            format = format.format(8)
        else:
            format = format.format(3)

        self.fields.id = format.format(message.arbitration_id)

        try:
            self.fields.message = self.frame._name
        except AttributeError:
            self.fields.message = '-'

        self.fields.length = '{} B'.format(message.dlc)
        self.fields.signal = ''
        # TODO: quit repeating (98476589238759)
        self.fields.value = ' '.join(['{:02X}'.format(byte) for byte in message.data])
        if self.last_time == message.timestamp:
            raise Exception('message already received')
        if self.last_time is None:
            self.fields.dt = '-'
        else:
            self.fields.dt = '{:.4f}'.format(message.timestamp - self.last_time)
        self.last_time = message.timestamp

        Frame.message_received(self, message)

    def unique(self):
        return self.fields.id

    def set_data(self, data):
        self.fields.value = data
        self.update()
        self.frame.update_from_signals()

class SignalNode(Signal, TreeNode):
    def __init__(self, signal, frame, tx=False, connect=None, tree_parent=None, parent=None):
        Signal.__init__(self, signal=signal, frame=frame, connect=connect, parent=parent)
        TreeNode.__init__(self, tx=tx, parent=tree_parent)

        self.fields = TxRxColumns(id=self.signal.getMsbReverseStartbit(),
                                  message='',
                                  signal=signal._name,
                                  length='{} b'.format(signal._signalsize),
                                  value='-',
                                  dt=None)
        self.last_time = None

    def unique(self):
        # TODO: make it more unique
        return str(self.fields.id) + '__'

    def set_value(self, value):
        Signal.set_value(self, value)
        s = self.signal
        v = str(self.value)
        try:
            value = '{} ({})'.format(s._values[str(v)], v)
        except KeyError:
            value = v

        if s._unit is not None:
            if len(s._unit) > 0:
                value += ' [{}]'.format(s._unit)
        self.fields.value = value

    def set_data(self, data):
        self.value = data
        self.fields.value = data
        self.frame.update_from_signals()


class TxRx(TreeNode, QtCanListener):
    # TODO: just Rx?
    changed = pyqtSignal(TreeNode, int, TreeNode, int)
    added = pyqtSignal(TreeNode)

    def __init__(self, tx, matrix=None, bus=None, parent=None):
        TreeNode.__init__(self)
        QtCanListener.__init__(self, parent=parent)

        self.bus = bus

        self.tx = tx
        self.rx = not self.tx
        self.matrix = matrix
        self.messages = {}

        if self.rx:
            self.message_received_signal.connect(self.message_received)

        if self.tx:
            for frame in self.matrix._fl._list:
                message = can.Message()
                message.arbitration_id = frame._Id
                message.id_type = frame._extended
                message.dlc = frame._Size
                self.add_message(message, tx=True)

    def set_node_id(self, node_id):
        # TODO: I think this can go away
        self.node_id = node_id

    def add_message(self, message=can.Message(), tx=False):
        try:
            frame = self.matrix.frameById(message.arbitration_id)
        except AttributeError:
            frame = None

        id = (message.arbitration_id, message.id_type)

        message_node = frame.frame
        message_node.send.connect(self.send)
        self.messages[id] = message_node
        self.append_child(message_node)
        self.added.emit(message_node)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        id = (msg.arbitration_id, msg.id_type)

        try:
            self.messages[id].extract_message(msg)
            # TODO: be more judicious in describing what changed
            #       and also don't change just column 5...
            self.changed.emit(self.messages[id], TxRxColumns.indexes.value,
                              self.messages[id], TxRxColumns.indexes.dt)
            self.changed.emit(self.messages[id].children[0], TxRxColumns.indexes.value,
                              self.messages[id].children[-1], TxRxColumns.indexes.value)
        except KeyError:
            self.add_message(msg)

    def unique(self):
        # TODO: actually identify the object
        return '-'

    @pyqtSlot(can.Message)
    def send(self, message):
        self.bus.send(message)

    def __str__(self):
        return 'Indexes: \n' + '\n'.join([str(i) for i in self.children])


class TxRxColumns:
    def __init__(self, id, length, message, signal, value, dt):
        self.id = id
        self.length = length
        self.message = message
        self.signal = signal
        self.value = value
        self.dt = dt

    def none():
        return TxRxColumns(None, None, None, None, None, None)

    def __len__(self):
        return 6

    def __getitem__(self, index):
        if index == TxRxColumns.indexes.id:
            return self.id
        if index == TxRxColumns.indexes.length:
            return self.length
        if index == TxRxColumns.indexes.message:
            return self.message
        if index == TxRxColumns.indexes.signal:
            return self.signal
        if index == TxRxColumns.indexes.value:
            return self.value
        if index == TxRxColumns.indexes.dt:
            return self.dt

        raise IndexError('column index out of range')

TxRxColumns.indexes = TxRxColumns(0, 1, 2, 3, 4, 5)


class TxRxModel(QAbstractItemModel):
    # TODO: seems like a lot of boilerplate which could be put in an abstract class
    #       (wrapping the abstract class?  hmmm)

    def __init__(self, root, parent=None):
        QAbstractItemModel.__init__(self, parent=parent)

        self.root = root
        self.headers = TxRxColumns(id='ID',
                                   length='Length',
                                   message='Message',
                                   signal='Signal',
                                   value='Value',
                                   dt='dt')

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

    def flags(self, index):
        flags = QAbstractItemModel.flags(self, index)

        # TODO: only if Tx
        if self.node_from_index(index).tx:
            if index.column() == TxRxColumns.indexes.value:
                flags |= Qt.ItemIsEditable

        return flags

    def setData(self, index, data, role=None):
        if role == QtCore.Qt.EditRole:
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

        if role != Qt.DisplayRole:
            return QVariant()

        node = self.node_from_index(index)

        if index.column() == len(self.headers):
            return QVariant(node.unique())
        else:
            try:
                return QVariant(node.fields[index.column()])
            except IndexError:
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

    @pyqtSlot(TreeNode, int, TreeNode, int)
    def changed(self, start_node, start_column, end_node, end_column):
        start_index = self.index_from_node(start_node)
        start_index = self.index(start_index.row(), start_column, start_index.parent())
        if end_node is not start_node:
            end_index = self.index_from_node(end_node)
            end_index = self.index(end_index.row(), end_column, end_index.parent())
        else:
            end_index = start_index
        self.dataChanged.emit(start_index, end_index)

    @pyqtSlot(TreeNode)
    def added(self, message):
        # TODO: this is just a tad bit broad...
        self.beginResetModel()
        self.endResetModel()


def main(args=None):
    import sys

    if args is None:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--can', default='../AFE_CAN_ID247_FACTORY.dbc')
        parser.add_argument('--generate', '-g', action='store_true')
        args = parser.parse_args()

    # TODO: get this outta here
    default = {
        'Linux': {'bustype': 'socketcan', 'channel': 'vcan0'},
        'Windows': {'bustype': 'pcan', 'channel': 'PCAN_USBBUS1'}
    }[platform.system()]
    bus = can.interface.Bus(**default)

    # TODO: the repetition here is not so pretty
    matrix_rx = importany.importany(args.can)
    matrix_tx = copy.deepcopy(matrix_rx)
    matrix_widgets = copy.deepcopy(matrix_rx)

    frames_rx = [MessageNode(message=None, frame=frame) for frame in matrix_rx._fl._list]
    frames_tx = [MessageNode(message=None, frame=frame, tx=True) for frame in matrix_tx._fl._list]

    frames_widgets = [Frame(frame) for frame in matrix_widgets._fl._list]
    for frame in frames_widgets:
        [Signal(signal, frame=frame) for signal in frame.frame._signals]

    rx = TxRx(tx=False, matrix=matrix_rx)
    rx_model = TxRxModel(rx)

    rx.changed.connect(rx_model.changed)
    rx.added.connect(rx_model.added)

    tx = TxRx(tx=True, matrix=matrix_tx, bus=bus)
    tx_model = TxRxModel(tx)

    tx.changed.connect(tx_model.changed)
    tx.added.connect(tx_model.added)
    notifier = can.Notifier(bus, frames_widgets + [rx])

    if args.generate:
        print('generating')
        start_time = time.monotonic()

        frame_name = 'MasterMeasuredPower'
        signal_name = 'ReactivePower_measured'
        frame = Frame(matrix_tx.frameByName(frame_name))
        signal = Signal(frame.frame.signalByName(signal_name), frame)

        message = can.Message(extended_id=frame.frame._extended,
                              arbitration_id=frame.frame._Id,
                              dlc=frame.frame._Size)

        last_send = 0
        while True:
            time.sleep(0.010)
            now = time.monotonic()
            if now - last_send > 0.100:
                last_send = now
                elapsed_time = time.monotonic() - start_time
                value = math.sin(elapsed_time) / 2
                value += 0.5
                value = round(value * 100)
                print('{:.3f}: {}'.format(elapsed_time, value))
                message.data = frame.pack([0, value])
                bus.send(message)
        sys.exit(0)

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = Window(matrix_widgets, tx_model=tx_model, rx_model=rx_model)

    window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
