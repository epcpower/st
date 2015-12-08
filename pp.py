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


# TODO: all these QObjects should be able to take parents

class Signal(QObject):
    _my_signal = pyqtSignal(int)

    def __init__(self, signal, connect=None):
        signal.signal = self
        self.signal = signal
        # TODO: what about QObject parameters
        QObject.__init__(self)
        self.value = None

        if connect is not None:
            self.connect(connect)

    def connect(self, target):
        self._my_signal.connect(target)

    def set_value(self, value):
        value = copy.deepcopy(value)
        self.value = value
        self._my_signal.emit(value)


class Frame(QObject, can.Listener):
    message_received_signal = pyqtSignal(can.Message)

    def __init__(self, frame):
        QObject.__init__(self)
        can.Listener.__init__(self)

        self.frame = frame

        self.message_received_signal.connect(self.message_received)

    def unpad(self):
        self.frame._signals = [s for s in self.frame._signals
                               if s._name != '__padding__']

    def pad(self):
        self.unpad()
        self.frame._signals.sort(key=lambda x: x._startbit)
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
            startbit = signal._startbit
            if signal._byteorder == 0:
                startbit -= min(signal._signalsize, 7)
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
            l = []
            for s, v in zip(self.frame._signals, unpacked):
                try:
                    value = '{} ({})'.format(s._values[v], v)
                except KeyError:
                    value = v
                string = '  {}: {}'.format(s._name, value)
                if s._unit is not None:
                    if len(s._unit) > 0:
                        string += ' [{}]'.format(s._unit)
                l.append(string)
                try:
                    s.signal.set_value(v)
                except AttributeError:
                    pass

    # TODO: make a class inheriting from can.Listener to translate it to Qt signals
    def on_message_received(self, msg):
        self.message_received_signal.emit(copy.deepcopy(msg))

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if msg.arbitration_id == self.frame._Id and msg.id_type == self.frame._extended:
            self.unpack(msg.data)


import generated.pp_ui as ui
from PyQt5 import QtCore, QtWidgets, QtGui
class Window(QtWidgets.QMainWindow):
    def __init__(self, matrix, txrx_model, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.ui = ui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.txrx.setModel(txrx_model)

        children = self.findChildren(QtCore.QObject)
        targets = [c for c in children if
                   c.property('frame') and c.property('signal')]

        for target in targets:
            frame_name = target.property('frame')
            signal_name = target.property('signal')

            frame = Frame(matrix.frameByName(frame_name))
            signal = Signal(frame.frame.signalByName(signal_name))

            signal.connect(target.setValue)
            target.setMinimum(0)#signal._min)
            target.setMaximum(100)#signal._max)


class TreeNode:
    def __init__(self,  parent=None):
        self.last = None

        self.parent = None
        self.set_parent(parent)
        self.children = []

    def set_parent(self, parent):
        self.parent = parent
        if self.parent is not None:
            self.parent.append_child(self)

    def append_child(self, child):
        self.children.append(child)
        child.parent = self

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


class MessageNode(TreeNode):
    def __init__(self, message, frame=None, parent=None):
        TreeNode.__init__(self, parent)

        self.id = None
        self.length = None
        self.message = None
        self.signal = None
        self.value = None
        self.dt = None
        self.last_time = None

        self.frame = frame

        try:
            for signal in self.frame._signals:
                self.append_child(SignalNode(signal))
        except AttributeError:
            pass

        self.extract_message(message)

    def extract_message(self, message, verify=True):
        if verify:
            # TODO: make sure the message matches the id/type and length
            pass

        self.message = message

        # TODO: should this formatting be done in the other place?
        format = '0x{{:0{}X}}'
        if message.id_type:
            format = format.format(8)
        else:
            format = format.format(3)

        self.id = format.format(message.arbitration_id)

        try:
            self.message = self.frame._name
        except AttributeError:
            self.message = '-'

        self.length = '{} B'.format(message.dlc)
        self.signal = ''
        self.value = ' '.join(['{:02X}'.format(byte) for byte in message.data])
        if self.last_time is None:
            self.dt = '-'
        else:
            self.dt = message.timestamp - self.last_time
            self.dt = '{:.4f}'.format(self.dt)
        self.last_time = message.timestamp

        for child in self.children:
            child.update()

    def unique(self):
        return self.id


class SignalNode(TreeNode):
    def __init__(self, signal, parent=None):
        TreeNode.__init__(self, parent)

        self.id = signal._startbit
        self.message = ''
        self.signal_object = signal
        self.signal = signal._name
        self.length = '{} b'.format(signal._signalsize)
        self.value = '-'
        self.dt = None
        self.last_time = None

    def unique(self):
        # TODO: make it more unique
        return str(self.id) + '__'

    def update(self):
        self.value = self.signal_object.signal.value


class TxRx(TreeNode, can.Listener, QObject):
    # TODO: just Rx?
    changed = pyqtSignal(TreeNode, int)
    added = pyqtSignal(TreeNode)
    message_received_signal = pyqtSignal(can.Message)

    def __init__(self, matrix=None, parent=None):
        TreeNode.__init__(self, parent)
        QObject.__init__(self)

        self.matrix = matrix
        self.messages = {}

        self.message_received_signal.connect(self.message_received)

    def set_node_id(self, node_id):
        # TODO: I think this can go away
        self.node_id = node_id

    def on_message_received(self, msg):
        self.message_received_signal.emit(copy.deepcopy(msg))

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        id = (msg.arbitration_id, msg.id_type)

        try:
            self.messages[id].extract_message(msg)
            # TODO: be more judicious in describing what changed
            #       and also don't change just column 5...
            self.changed.emit(self.messages[id], 4)
            self.changed.emit(self.messages[id], 5)
            for signal in self.messages[id].children:
                self.changed.emit(signal, 4)
        except KeyError:
            try:
                frame = self.matrix.frameById(msg.arbitration_id)
            except AttributeError:
                frame = None

            message_node = MessageNode(msg, frame=frame)
            self.messages[id] = message_node
            self.append_child(message_node)
            self.added.emit(message_node)

    def unique(self):
        # TODO: actually identify the object
        return '-'

    def __str__(self):
        return 'Indexes: \n' + '\n'.join([str(i) for i in self.children])


class TxRxModel(QAbstractItemModel):
    # TODO: seems like a lot of boilerplate which could be put in an abstract class
    #       (wrapping the abstract class?  hmmm)

    def __init__(self, root, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.root = root
        self.headers = ['ID', 'Length', 'Message', 'Signal', 'Value', 'dt']
        # TODO: refactoring like below might make things quicker?
        # headers = ['ID', 'Length', 'Message', 'Signal', 'Value', 'dt']
        # self.headers = {}
        # for i, header in enumerate(headers):
        #     self.headers[header] = i
        self.columns = len(self.headers)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

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

        if index.column() == self.headers.index('ID'):
            return QVariant(node.id)

        elif index.column() == self.headers.index('Length'):
            return QVariant(node.length)

        elif index.column() == self.headers.index('Message'):
            return QVariant(node.message)

        elif index.column() == self.headers.index('Signal'):
            return QVariant(node.signal)

        elif index.column() == self.headers.index('Value'):
            return QVariant(node.value)

        elif index.column() == self.headers.index('dt'):
            return QVariant(node.dt)

        elif index.column() == len(self.headers):
            return QVariant(node.unique())

        else:
            return QVariant()

    def columnCount(self, parent):
        return self.columns

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

        parent = node.parent

        if parent is None:
            return QModelIndex()

        grandparent = parent.parent
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
        return self.match(self.index(0, len(self.headers), QModelIndex()),
                          Qt.DisplayRole,
                          node.unique(),
                          1,
                          Qt.MatchRecursive)

    @pyqtSlot(TreeNode, int)
    def changed(self, node, column):
        index = self.index_from_node(node)[0]
        index = self.index(index.row(), column, index.parent())
        self.dataChanged.emit(index, index)

    @pyqtSlot(TreeNode)
    def added(self, message):
        # TODO: this is just a tad bit broad...
        self.beginResetModel()
        self.endResetModel()


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--can', default='../AFE_CAN_ID247_FACTORY.dbc')
    parser.add_argument('--generate', '-g', action='store_true')
    args = parser.parse_args()

    print('importing')
    matrix = importany.importany(args.can)
    frames = [Frame(frame) for frame in matrix._fl._list]
    for frame in frames:
        [Signal(signal) for signal in frame.frame._signals]

    # TODO: get this outta here
    default = {
        'Linux': {'bustype': 'socketcan', 'channel': 'vcan0'},
        'Windows': {'bustype': 'pcan', 'channel': 'PCAN_USBBUS1'}
    }[platform.system()]
    bus = can.interface.Bus(**default)

    txrx = TxRx(matrix=matrix)
    txrx_model = TxRxModel(txrx)

    txrx.changed.connect(txrx_model.changed)
    txrx.added.connect(txrx_model.added)
    notifier = can.Notifier(bus, frames + [txrx])

    if args.generate:
        print('generating')
        start_time = time.monotonic()

        frame_name = 'MasterMeasuredPower'
        signal_name = 'ReactivePower_measured'
        frame = Frame(matrix.frameByName(frame_name))
        signal = Signal(frame.frame.signalByName(signal_name))

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

    window = Window(matrix, txrx_model)

    window.show()
    sys.exit(app.exec_())
