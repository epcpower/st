import bitstruct
import can
from canmatrix import canmatrix
import copy
import functools
import math
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot, QTimer)
import re
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Signal(QObject):
    # TODO: but some (progress bar, etc) require an int!
    value_changed = pyqtSignal(float)

    def __init__(self, signal, frame, connect=None, parent=None):
        # TODO: what about QObject parameters
        QObject.__init__(self, parent=parent)

        # self._attributes = signal._attributes # {dict} {'GenSigStartValue': '0.0', 'LongName': 'Enable'}
        try:
            self.default_value = signal._attributes['GenSigStartValue']
        except KeyError:
            self.default_value = None
        else:
            self.default_value = float(self.default_value)
        self.long_name = signal._attributes.get('LongName', None)
        self.hexadecimal_output = signal._attributes.get('HexadecimalOutput',
                                                         None)
        self.hexadecimal_output = self.hexadecimal_output is not None
        self.little_endian = signal._is_little_endian # {int} 0
        self.comment = signal._comment # {str} 'Run command.  When set to a value of \\'Enable\\', causes transition to grid forming or grid following mode depending on whether AC power is detected.  Must be set to \\'Disable\\' to leave POR or FAULTED state.'
        # TODO: maybe not use a string, but used to help with decimal places
        self.factor = signal._factor
        try:
            self.max = float(signal._max) # {str} '1'
        except ValueError:
            # TODO: default based on signal range
            self.max = None
        try:
            self.min = float(signal._min) # {str} '0'
        except ValueError:
            # TODO: default based on signal range
            self.min = None
        try:
            self.offset = float(signal._offset) # {str} '0'
        except ValueError:
            self.offset = 0

        if signal._multiplex == 'Multiplexor':
            self.multiplex = None
        else:
            self.multiplex = signal._multiplex # {NoneType} None

        self.name = signal._name # {str} 'Enable_command'
        # self._receiver = signal._receiver # {str} ''
        self.signal_size = int(signal._signalsize) # {int} 2
        self.start_bit = int(signal.getStartbit()) # {int} 0
        self.unit = signal._unit # {str} ''
        self.enumeration = {int(k): v for k, v in signal._values.items()} # {dict} {'0': 'Disable', '2': 'Error', '1': 'Enable', '3': 'N/A'}
        self.signed = signal._is_signed
        self.float = signal._is_float

        self.value = None
        self.scaled_value = None
        self.full_string = None

        self.frame = frame
        # TODO: put this into the frame!
        self.frame.signals.append(self)

        self.enumeration_format_re = {'re': '^\[(\d+)\]',
                                      'format': '[{v}] {s}'}

        if connect is not None:
            self.connect(connect)

    def get_human_value(self):
        # TODO: handle offset
        if self.value is None:
            return None

        value = self.offset + (self.value * float(self.factor))

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

        value = (value - self.offset) / self.factor
        value = round(value)
        self.set_value(value)

    def enumeration_string(self, value):
        return self.enumeration_format_re['format'].format(
                v=value, s=self.enumeration[value])

    def enumeration_strings(self):
        items = list(self.enumeration)
        items.sort()
        items = [self.enumeration_string(i) for i in items]

        return items

    def get_decimal_places(self):
        try:
            return self.decimal_places
        except AttributeError:
            x = self.factor
            # http://stackoverflow.com/a/3019027/228539
            max_digits = 14
            int_part = int(abs(x))
            magnitude = 1 if int_part == 0 else int(math.log10(int_part)) + 1
            if magnitude >= max_digits:
                return (magnitude, 0)
            frac_part = abs(x) - int_part
            multiplier = 10 ** (max_digits - magnitude)
            frac_digits = multiplier + int(multiplier * frac_part + 0.5)
            while frac_digits % 10 == 0:
                frac_digits /= 10
            scale = int(math.log10(frac_digits))

            self.decimal_places = scale

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
                # TODO: CAMPid 94562754956589992752348667
                enum_string = self.enumeration[value]
                self.full_string = self.enumeration_format_re['format'].format(
                        s=enum_string, v=value)
            except KeyError:
                # TODO: this should be a subclass or something
                if self.name == '__padding__':
                    self.full_string = '__padding__'
                elif self.hexadecimal_output:
                    format = '{{:0{}X}}'.format(math.ceil(self.signal_size/math.log2(16)))
                    self.full_string = format.format(int(self.value))
                else:
                    # TODO: CAMPid 9395616283654658598648263423685
                    # TODO: and _offset...

                    self.scaled_value = (
                        self.offset + (float(self.value) * self.factor)
                    )

                    self.full_string = self.format_float(self.scaled_value)

                    if self.unit is not None:
                        if len(self.unit) > 0:
                            self.full_string += ' [{}]'.format(self.unit)

                    value = self.scaled_value

            self.value_changed.emit(value)

    def force_value_changed(self):
        value = self.scaled_value
        if value is None:
            value = 0
        self.value_changed.emit(value)

    def format_float(self, value=None):
        if value is None:
            value = self.scaled_value
        return '{{:.{}f}}'.format(self.get_decimal_places()).format(value)

    def format(self):
        if self.float:
            types = {
                32: 'f',
                64: 'd'
            }
            try:
                type = types[self.signal_size]
            except KeyError:
                raise Exception(
                    'float type only supports lengths in [{}]'.
                    format(', '.join([str(t) for t in types.keys()]))
                )
        else:
            type = 's' if self.signed else 'u'

        return '{}{}{}'.format(
                '<' if self.little_endian else '>',
                type,
                self.signal_size)


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

    def __init__(self, frame, multiplex_value=None,
                 signal_class=Signal, parent=None):
        QtCanListener.__init__(self, self.message_received, parent=parent)

        self.id = frame._Id # {int} 16755521
        # self._SignalGroups = frame._SignalGroups # {list} []
        self.size = frame._Size # {int} 8
        # self._Transmitter = frame._Transmitter # {list} []
        # self._attributes = frame._attributes # {dict} {'GenMsgCycleTime': '200'}
        self.cycle_time = frame._attributes.get('GenMsgCycleTime', None)
        self.mux_name = frame._attributes.get('mux_name', None)
        self.comment = frame._comment # {str} 'Operational commands are received by the module via control bits within this message.'
        self.extended = bool(frame._extended) # {int} 1
        self.name = frame._name # {str} 'CommandModeControl'
        # self._receiver = frame._receiver # {list} []
        # self._signals = frame._signals # {list} [<canmatrix.canmatrix.Signal object at 0x7fddf8053fd0>, <canmatrix.canmatrix.Signal object at 0x7fddf8054048>, <canmatrix.canmatrix.Signal object at 0x7fddf80543c8>, <canmatrix.canmatrix.Signal object at 0x7fddf8054470>, <canmatrix.canmatrix.Signal object

        self.padded = False

        self._cyclic_requests = {}
        self._cyclic_period = None
        self.user_send_control = True
        self.timer = QTimer()
        _update_and_send = functools.partial(self._send, update=True)
        self.timer.timeout.connect(_update_and_send)

        self.signals = []
        for signal in frame._signals:
            if (multiplex_value is None or
                        str(signal._multiplex) == multiplex_value):
                neo_signal = signal_class(signal=signal, frame=self)

                factor = neo_signal.factor
                if factor is None:
                    factor = 1

                offset = neo_signal.offset
                if offset is None:
                    offset = 0

                default_value = neo_signal.default_value
                if default_value is None:
                    default_value = 0

                neo_signal.set_human_value(offset + (default_value * factor))

    def signal_by_name(self, name):
        try:
            return next(s for s in self.signals if s.name == name)
        except StopIteration:
            return None

    def unpad(self):
        if self.padded:
            self.frame._signals = [s for s in self.frame._signals
                                   if s._name != '__padding__']

            self.padded = False

    def pad(self):
        if not self.padded:
            # TODO: use getMsbStartbit() if intel/little endian
            #       and search for all other uses
            self.signals.sort(key=lambda x: x.start_bit)
            # TODO: get rid of this, yuck
            Matrix_Pad = lambda start_bit, length: canmatrix.Signal(
                name='__padding__',
                startBit=start_bit,
                signalSize=length,
                is_little_endian=0)
            def Matrix_Pad_Fixed(start_bit, length):
                pad = Matrix_Pad(start_bit, length)
                pad.setStartbit(start_bit)
                return pad
            Pad = lambda start_bit, length: Signal(
                signal=Matrix_Pad_Fixed(start_bit, length),
                frame=self
            )
            # TODO: 1 or 0, which is the first bit per canmatrix?
            bit = 0
            # pad for unused bits
            padded_signals = []
            unpadded_signals = list(self.signals)
            for signal in unpadded_signals:
                startbit = signal.start_bit
                if startbit < bit:
                    raise Exception('{}({}):{}: too far ahead!'
                                    .format(self.name,
                                            self.mux_name,
                                            signal.name))
                padding = startbit - bit
                if padding:
                    pad = Pad(bit, padding)
                    padded_signals.append(pad)
                    bit += pad.signal_size
                padded_signals.append(signal)
                bit += signal.signal_size
            # TODO: 1 or 0, which is the first bit per canmatrix?
            padding = (self.size * 8) - bit
            if padding < 0:
                # TODO: fix the common issue so the exception can be used
                # raise Exception('frame too long!')
                print('Frame too long!  (but this is expected for now since the DBC seems wrong)')
            elif padding > 0:
                pad = Pad(bit, padding)
                padded_signals.append(pad)

            self.signals = padded_signals
            self.padded = True

    def format(self):
        try:
            fmt = self.format_str
        except AttributeError:
            fmt = [s.format() for s in self.signals]
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
            for signal in self.signals:
                try:
                    value = function(signal)
                except:
                    value = 0

                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = 0
                data.append(value)

        return bitstruct.pack(self.format(), *data)

    def unpack(self, data, report_error=True):
        rx_length = len(data)
        if rx_length != self.size and report_error:
            print('Received message 0x{self.id:08X} with length {rx_length}, expected {self.size}'.format(**locals()))
        else:
            self.pad()

            try:
                bitstruct_fmt = self.bitstruct_fmt
            except AttributeError:
                bitstruct_fmt = bitstruct._parse_format(self.format())
                self.bitstruct_fmt = bitstruct_fmt

            unpacked = bitstruct.unpack(bitstruct_fmt, data)
            for s, v in zip(self.signals, unpacked):
                s.set_value(v)

    @pyqtSlot()
    def _send(self, update=False):
        if update:
            self.data = self.pack(self)

        self.send.emit(self.to_message())

        try:
            sent = self._sent
        except AttributeError:
            pass
        else:
            sent()

    def send_now(self):
        self._send(update=True)

    def cyclic_request(self, caller, period):
        if period is None:
            try:
                del self._cyclic_requests[caller]
            except KeyError:
                pass
        else:
            # period will be able to converted to a float, test
            # sooner rather than later for easier debugging
            float(period)
            self._cyclic_requests[caller] = period

        periods = [float(v) for v in self._cyclic_requests.values()]
        new_period = min(periods) if len(periods) > 0 else None

        if new_period is not None:
            if new_period <= 0:
                new_period = None

        if new_period != self._cyclic_period:
            self._cyclic_period = new_period

            if self._cyclic_period is None:
                self.timer.stop()
            else:
                self.timer.setInterval(
                    int(round(float(self._cyclic_period) * 1000)))
                if not self.timer.isActive():
                    self.timer.start()

    def to_message(self):
        try:
            data = self.data
        except AttributeError:
            data = [0] * self.size

        return can.Message(extended_id=self.extended,
                           arbitration_id=self.id,
                           dlc=self.size,
                           data=data)

        return None

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if (msg.arbitration_id == self.id and
                bool(msg.id_type) == self.extended):
            self.unpack(msg.data)


class Neo(QtCanListener):
    def __init__(self, matrix, frame_class=Frame, signal_class=Signal,
                 rx_interval=0, bus=None, node_id_adjust=None, parent=None):
        QtCanListener.__init__(self, self.message_received, parent=parent)

        self.frame_rx_timestamps = {}
        self.frame_rx_interval = rx_interval

        frames = []

        for frame in matrix._fl._list:
            if node_id_adjust is not None:
                frame._Id = node_id_adjust(frame._Id)
            multiplex_signal = None
            for signal in frame._signals:
                if signal._multiplex == 'Multiplexor':
                    multiplex_signal = signal
                    break

            if multiplex_signal is None:
                neo_frame = frame_class(frame=frame)
                # for signal in frame._signals:
                #     signal = signal_class(signal=signal, frame=neo_frame)
                #     signal.set_human_value(signal.default_value *
                #                            signal.factor[float])
                frames.append(neo_frame)
            else:
                # Make a frame with just the multiplexor entry for
                # parsing messages later
                # TODO: add __copy__() and __deepcopy__() to canmatrix
                multiplex_frame = canmatrix.Frame(
                        name=frame._name,
                        Id=frame._Id,
                        dlc=frame._Size,
                        transmitter=frame._Transmitter)
                multiplex_frame._extended = frame._extended
                # TODO: add __copy__() and __deepcopy__() to canmatrix
                matrix_signal = canmatrix.Signal(
                        name=multiplex_signal._name,
                        startBit=multiplex_signal._startbit,
                        signalSize=multiplex_signal._signalsize,
                        is_little_endian=multiplex_signal._is_little_endian,
                        is_signed=multiplex_signal._is_signed,
                        factor=multiplex_signal._factor,
                        offset=multiplex_signal._offset,
                        min=multiplex_signal._min,
                        max=multiplex_signal._max,
                        unit=multiplex_signal._unit,
                        multiplex=multiplex_signal._multiplex)
                multiplex_frame.addSignal(matrix_signal)
                multiplex_neo_frame = frame_class(frame=multiplex_frame)
                frames.append(multiplex_neo_frame)

                multiplex_neo_frame.multiplex_signal =\
                    multiplex_neo_frame.signals[0]

                multiplex_neo_frame.multiplex_frames = {}

                for multiplex_value, multiplex_name in multiplex_signal._values.items():
                    # For each multiplexed frame, make a frame with
                    # just those signals.
                    matrix_frame = canmatrix.Frame(
                            name=frame._name,
                            Id=frame._Id,
                            dlc=frame._Size,
                            transmitter=frame._Transmitter)
                    matrix_frame._extended = frame._extended
                    matrix_frame.addAttribute('mux_name', multiplex_name)
                    matrix_signal = canmatrix.Signal(
                            name=multiplex_signal._name,
                            startBit=multiplex_signal._startbit,
                            signalSize=multiplex_signal._signalsize,
                            is_little_endian=multiplex_signal._is_little_endian,
                            is_signed=multiplex_signal._is_signed,
                            factor=multiplex_signal._factor,
                            offset=multiplex_signal._offset,
                            min=multiplex_signal._min,
                            max=multiplex_signal._max,
                            unit=multiplex_signal._unit,
                            multiplex=multiplex_signal._multiplex)
                    # neo_signal = signal_class(signal=matrix_signal, frame=multiplex_neo_frame)
                    matrix_frame.addSignal(matrix_signal)

                    for signal in frame._signals:
                        if str(signal._multiplex) == multiplex_value:
                            matrix_frame.addSignal(signal)

                    neo_frame = frame_class(frame=matrix_frame)
                    for signal in neo_frame.signals:
                        if signal.multiplex is None:
                            signal.set_value(multiplex_value)
                    frames.append(neo_frame)
                    multiplex_neo_frame.\
                        multiplex_frames[int(multiplex_value)] = neo_frame

        if bus is not None:
            for frame in frames:
                frame.send.connect(bus.send)

        self.frames = frames

    def frame_by_id(self, id):
        try:
            return next(f for f in self.frames if f.id == id)
        except StopIteration:
            return None

    def frame_by_name(self, name):
        try:
            return next(f for f in self.frames if f.name == name)
        except StopIteration:
            return None

    def get_multiplex(self, message):
        base_frame = self.frame_by_id(message.arbitration_id)

        if not hasattr(base_frame, 'multiplex_frames'):
            frame = base_frame
            multiplex_value = None
        else:
            # finish the multiplex thing
            base_frame.unpack(message.data, report_error=False)
            multiplex_value = base_frame.multiplex_signal.value
            try:
                frame = base_frame.multiplex_frames[multiplex_value]
            except KeyError:
                return (None, None)

        return (frame, multiplex_value)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        frame = self.frame_by_id(msg.arbitration_id)
        if frame is not None:
            last = self.frame_rx_timestamps.get(frame,
                                                -self.frame_rx_interval)
            if msg.timestamp - last >= self.frame_rx_interval:
                self.frame_rx_timestamps[frame] = msg.timestamp
                frame.message_received_signal.emit(msg)


def format_identifier(identifier, extended):
    f = '0x{{:0{}X}}'

    if extended:
        f = f.format(8)
    else:
        f = f.format(3)

    return f.format(identifier)

def format_data(data):
    return ' '.join(['{:02X}'.format(byte) for byte in data])
