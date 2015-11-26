#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import sys
# sys.path.append('../canmatrix')

import bitstruct
import can
import copy
import platform
import threading

import canmatrix.importdbc as importdbc
import canmatrix.canmatrix as canmatrix

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

# def swap_endianness(x, bytes):
#     format = '{{:0{}x}}'.format(2*bytes)
#     return bitstruct.byteswap('8', bytearray.fromhex(format.format(x)))


# class Signal(QObject, canmatrix.Signal):
#     _my_signal = pyqtSignal(int)
#
#     def __init__(self, *args, **kwargs):
#         canmatrix.Signal.__init__(self, *args, **kwargs)
#         # TODO: what about QObject
#         print('boo')
#
#     def connect(self, target):
#         self._my_signal.connect(target)
#
#     def set_value(self, value):
#         self._my_value = value
#         self._my_signal.emit(value)
#
# canmatrix.Signal = Signal
# print('overwritten')


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
        bit = 1
        # pad for unused bits
        padded_signals = []
        for signal in self.frame._signals:
            if signal._startbit < bit:
                raise Exception('too far ahead!')
            padding = signal._startbit - bit
            if padding:
                pad = Pad(bit, padding)
                padded_signals.append(pad)
                bit += pad._signalsize
            padded_signals.append(signal)
            bit += signal._signalsize
        # TODO: 1 or 0, which is the first bit per canmatrix?
        padding = (self.frame._Size * 8) - bit + 1
        if padding < 0:
            # TODO: fix the common issue so the exception can be used
            # raise Exception('frame too long!')
            print('Frame too long!  (but this is expected for now since the DBC seems wrong)')
        elif padding > 0:
            padded_signals.append(Pad(bit, padding))

        self.frame._signals = padded_signals

    def unpack(self, data):
        rx_length = len(data)
        if rx_length != self.frame._Size:
            print('Received message length {rx_length} != {self.frame._Size} received'.format(**locals()))
        else:
            # None is for handling padding
            types = {None: 'u', '+': 'u', '-': 's'}

            self.pad()

            format = ['{}{}'.format(types[s._valuetype], s._signalsize)
                      for s in self.frame._signals]
            format = ''.join(format)

            # TODO: endianness for bigger signals
            # bits required 2**math.ceil(math.log2(x))
            unpacked = bitstruct.unpack(format, data)
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

            print('\n'.join([e for e in l]))

    def on_message_received(self, msg):
        # print('on_message_received: {} - {}'.format(threading.current_thread(), msg.timestamp))
        # Hopefully this indirection provides some thread safety...
        self.message_received_signal.emit(copy.deepcopy(msg))

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        # print('message_received: start')
        # print('on_message_received: {} - {}'.format(threading.current_thread(), msg.timestamp))
        # TODO: yucky merging of the actual ID and the standard/extended bool
        # already addressed in upstream canmatrix but need to adjust here someday
        extended_mask = 0x80000000
        id = self.frame._Id & ~extended_mask
        extended  = True if self.frame._Id & extended_mask else False
        if msg.arbitration_id == id and msg.id_type == extended:
            print('Message {self.frame._name} received'.format(**locals()))
            self.unpack(msg.data)
        # print('message_received: stopped')


if __name__ == '__main__':
    import argparse
    import sys

    from PyQt5.QtWidgets import QApplication, QMainWindow, QProgressBar

    app = QApplication(sys.argv)
    progress = QProgressBar()

    window = QMainWindow()
    window.setCentralWidget(progress)

    parser = argparse.ArgumentParser()
    parser.add_argument('--dbc', default='../AFE_CAN_ID247_FACTORY.dbc')
    args = parser.parse_args()

    print('importing')
    matrix = importdbc.importDbc(args.dbc)
    frames = [Frame(frame) for frame in matrix._fl._list]

    # TODO: get this outta here
    default = {
        'Linux': {'bustype': 'socketcan', 'channel': 'vcan0'},
        'Windows': {'bustype': 'pcan', 'channel': 'PCAN_USBBUS1'}
    }[platform.system()]
    bus = can.interface.Bus(**default)

    notifier = can.Notifier(bus, frames)

    frame_name = 'MasterMeasuredPower'
    signal_name = 'ReactivePower_measured'
    Signal(matrix.frameByName(frame_name).signalByName(signal_name),
           connect=progress.setValue)
    progress.setMinimum(0)#signal._min)
    progress.setMaximum(10)#signal._max)

    print(threading.current_thread())

    window.show()
    sys.exit(app.exec_())
