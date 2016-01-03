import bitstruct
import can
from canmatrix import canmatrix
import copy
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2015, EPC Power Corp.'
__license__ = 'GPLv2+'


class Signal(QObject):
    # TODO: but some (progress bar, etc) require an int!
    _my_signal = pyqtSignal(float)

    def __init__(self, signal, frame, connect=None, parent=None):
        signal.signal = self
        self.signal = signal
        # TODO: what about QObject parameters
        QObject.__init__(self, parent=parent)
        self.value = None
        self.scaled_value = None
        self.full_string = None

        self.frame = frame

        if connect is not None:
            self.connect(connect)

    def connect(self, target):
        self._my_signal.connect(target)

    def set_human_value(self, value):
        value = copy.deepcopy(value)
        value = float(value)
        value /= float(self.signal._factor)
        value = round(value)
        self.set_value(value)

    def set_value(self, value):
        value = copy.deepcopy(value)
        self.value = value

        try:
            enum_string = self.signal._values[str(value)]
            self.full_string = '{} ({})'.format(enum_string, value)
        except KeyError:
            # TODO: this should be a subclass or something
            if self.signal._name == '__padding__':
                self.full_string = '__padding__'
            else:
                # TODO: and _offset...
                factor = self.signal._factor.rstrip('0.')
                decimal_point_index = factor.find('.')
                if decimal_point_index >= 0:
                    decimal_places = len(factor) - decimal_point_index - 1
                else:
                    decimal_places = 0

                self.scaled_value = float(self.value) * float(factor)

                f = '{{self.scaled_value:.{decimal_places}f}}'
                f = f.format(**locals())
                self.full_string = f.format(**locals())

                if self.signal._unit is not None:
                    if len(self.signal._unit) > 0:
                        self.full_string += ' [{}]'.format(self.signal._unit)

                value = self.scaled_value

        self._my_signal.emit(value)

    def format(self):
        # None is for handling padding
        types = {None: 'u', '+': 'u', '-': 's'}
        order = {None: '<', 0: '>', 1: '<'}

        return '{}{}{}'.format(
                order[self.signal._byteorder],
                types[self.signal._valuetype],
                self.signal._signalsize)


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
                Signal(signal=pad, frame=self)
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
            pad = Pad(bit, padding)
            Signal(signal=pad, frame=self)
            padded_signals.append(pad)

        self.frame._signals = padded_signals

    def format(self):
        fmt = [s.signal.format() for s in self.frame._signals]
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

        return None

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if (msg.arbitration_id == self.frame._Id and
                bool(msg.id_type) == bool(self.frame._extended)):
            self.unpack(msg.data)


def neotize(matrix, frame_class=Frame, signal_class=Signal, tx=False):
    frames = []

    for frame in matrix._fl._list:
        multiplex_signal = None
        for signal in frame._signals:
            if signal._multiplex == 'Multiplexor':
                multiplex_signal = signal
                break

        if multiplex_signal is None:
            neo_frame = frame_class(message=None,
                                    frame=frame,
                                    tx=tx)
            frames.append(neo_frame)
        else:
            # Make a frame with just the multiplexor entry for
            # parsing messages later
            # TODO: add __copy__() and __deepcopy__() to canmatrix
            multiplex_frame = canmatrix.Frame(
                    frame._Id,
                    frame._name,
                    frame._Size,
                    frame._Transmitter)
            multiplex_frame._extended = frame._extended
            # TODO: add __copy__() and __deepcopy__() to canmatrix
            matrix_signal = canmatrix.Signal(
                    multiplex_signal._name,
                    multiplex_signal._startbit,
                    multiplex_signal._signalsize,
                    multiplex_signal._byteorder,
                    multiplex_signal._valuetype,
                    multiplex_signal._factor,
                    multiplex_signal._offset,
                    multiplex_signal._min,
                    multiplex_signal._max,
                    multiplex_signal._unit,
                    multiplex_signal._reciever,
                    multiplex_signal._multiplex)
            multiplex_frame.addSignal(matrix_signal)
            neo_frame = frame_class(frame=multiplex_frame)
            frames.append(neo_frame)
            neo_signal = signal_class(signal=matrix_signal, frame=neo_frame)
            # TODO: shouldn't this be part of the constructor maybe?
            signal_class(signal=matrix_signal, frame=neo_frame)

            frame.multiplex_frame = multiplex_frame
            frame.multiplex_signal = multiplex_frame._signals[0]
            frame.multiplex_frames = {}

            for multiplex_value in multiplex_signal._values:
                # For each multiplexed frame, make a frame with
                # just those signals.
                matrix_frame = canmatrix.Frame(
                        frame._Id,
                        frame._name,
                        frame._Size,
                        frame._Transmitter)
                matrix_frame._extended = frame._extended
                matrix_signal = canmatrix.Signal(
                        multiplex_signal._name,
                        multiplex_signal._startbit,
                        multiplex_signal._signalsize,
                        multiplex_signal._byteorder,
                        multiplex_signal._valuetype,
                        multiplex_signal._factor,
                        multiplex_signal._offset,
                        multiplex_signal._min,
                        multiplex_signal._max,
                        multiplex_signal._unit,
                        multiplex_signal._reciever,
                        multiplex_signal._multiplex)
                matrix_frame.addSignal(matrix_signal)
                for signal in frame._signals:
                    if str(signal._multiplex) == multiplex_value:
                        signal_class(signal=signal, frame=neo_frame)
                        matrix_frame.addSignal(signal)

                neo_frame = frame_class(frame=matrix_frame)
                frames.append(neo_frame)
                frame.multiplex_frames[multiplex_value] = matrix_frame

    return frames
