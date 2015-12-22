import bitstruct
import can
from canmatrix import canmatrix
import copy
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot)


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
        self._send()

    @pyqtSlot()
    def _send(self):
        self.send.emit(self.to_message())

    def to_message(self):
        try:
            data = self.data
        except AttributeError:
            data = [0] * self.frame._Size

        return can.Message(extended_id=self.frame._extended,
                           arbitration_id=self.frame._Id,
                           dlc=self.frame._Size,
                           data=data)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if msg.arbitration_id == self.frame._Id and msg.id_type == self.frame._extended:
            self.unpack(msg.data)
