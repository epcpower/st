import bitstruct
import can
from canmatrix import canmatrix
import copy
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot)
import re
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2015, EPC Power Corp.'
__license__ = 'GPLv2+'


class Signal(QObject):
    # TODO: but some (progress bar, etc) require an int!
    value_changed = pyqtSignal(float)

    def __init__(self, signal, frame, connect=None, parent=None):
        signal.signal = self
        self.signal = signal
        # TODO: what about QObject parameters
        QObject.__init__(self, parent=parent)
        self.value = None
        self.scaled_value = None
        self.full_string = None

        self.frame = frame

        self.enumeration_format_re = {'re': '^\[(\d+)\]',
                                      'format': '[{v}] {s}'}

        if connect is not None:
            self.connect(connect)

    def get_human_value(self):
        # TODO: handle offset
        if self.value is None:
            return None

        value = self.value * float(self.signal._factor)

        return self.format_float(value)

    def set_human_value(self, value):
        # TODO: handle offset
        value = copy.deepcopy(value)
        try:
            # TODO: not the best for integers?
            value = float(value)
        except ValueError:
            if value in self.enumeration_strings():
                match = re.search(self.enumeration_format_re['re'], value)
                value = match.group(1)
                value = float(value)
            else:
                raise

        value /= float(self.signal._factor)
        value = round(value)
        self.set_value(value)

    def enumeration_string(self, value):
        return self.enumeration_format_re['format'].format(
                v=value, s=self.signal._values[value])

    def enumeration_strings(self):
        items = list(self.signal._values)
        items.sort()
        items = [self.enumeration_string(i) for i in items]

        return items

    def get_decimal_places(self):
        try:
            return self.decimal_places
        except AttributeError:
            factor_str = self.signal._factor.rstrip('0.')
            decimal_point_index = factor_str.find('.')
            if decimal_point_index >= 0:
                self.decimal_places = len(factor_str) - decimal_point_index - 1
            else:
                self.decimal_places = 0

        return self.decimal_places

    def set_value(self, value):
        if value is None:
            self.value = None
            self.full_string = '-'
        elif self.value != value:
            # TODO: be careful here, should all be int which is immutable
            #       and therefore safe but...  otherwise a copy would be
            #       needed
            self.value = value

            try:
                enum_string = self.signal._values[str(value)]
                self.full_string = self.enumeration_format_re['format'].format(
                        s=enum_string, v=value)
            except KeyError:
                # TODO: this should be a subclass or something
                if self.signal._name == '__padding__':
                    self.full_string = '__padding__'
                else:
                    # TODO: CAMPid 9395616283654658598648263423685
                    # TODO: and _offset...
                    try:
                        factor = self.factor
                    except AttributeError:
                        factor = float(self.signal._factor)
                        self.factor = factor

                    self.scaled_value = float(self.value) * factor

                    self.full_string = self.format_float(self.scaled_value)

                    if self.signal._unit is not None:
                        if len(self.signal._unit) > 0:
                            self.full_string += ' [{}]'.format(self.signal._unit)

                    value = self.scaled_value

            self.value_changed.emit(value)

    def format_float(self, value):
        return '{{:.{}f}}'.format(self.get_decimal_places()).format(value)

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

        self.padded = False

    def unpad(self):
        if self.padded:
            self.frame._signals = [s for s in self.frame._signals
                                   if s._name != '__padding__']

            self.padded = False

    def pad(self):
        if not self.padded:
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
                    # TODO: yucky to add out here
                    pad.setMsbReverseStartbit(bit)
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

            self.padded = True

    def format(self):
        try:
            fmt = self.format_str
        except AttributeError:
            fmt = [s.signal.format() for s in self.frame._signals]
            fmt = ''.join(fmt)
            self.format_str = fmt

        return fmt

    def update_from_signals(self, function=None):
        self.data = self.pack(self, function=function)

    def pack(self, data, function=None):
        self.pad()

        if data == self:
            if function is None:
                function = lambda s: s.value
            data = []
            for signal in self.frame._signals:
                try:
                    value = function(signal.signal)
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

            try:
                bitstruct_fmt = self.bitstruct_fmt
            except AttributeError:
                bitstruct_fmt = bitstruct._parse_format(self.format())
                self.bitstruct_fmt = bitstruct_fmt

            unpacked = bitstruct.unpack(bitstruct_fmt, data)
            for s, v in zip(self.frame._signals, unpacked):
                try:
                    s.signal.set_value(v)
                except AttributeError:
                    pass

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


def neotize(matrix, frame_class=Frame, signal_class=Signal):
    frames = []

    for frame in matrix._fl._list:
        multiplex_signal = None
        for signal in frame._signals:
            if signal._multiplex == 'Multiplexor':
                multiplex_signal = signal
                break

        if multiplex_signal is None:
            neo_frame = frame_class(frame=frame)
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
                matrix_signal.signal.set_value(multiplex_value)
                frames.append(neo_frame)
                frame.multiplex_frames[multiplex_value] = matrix_frame

    return frames


def get_multiplex(matrix, message):
    base_frame = matrix.frameById(message.arbitration_id)
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


def format_identifier(identifier, extended):
    f = '0x{{:0{}X}}'

    if extended:
        f = f.format(8)
    else:
        f = f.format(3)

    return f.format(identifier)

def format_data(data):
    return ' '.join(['{:02X}'.format(byte) for byte in data])
