import bitstruct
import can
from canmatrix import canmatrix
import copy
import epyqlib.utils.general
import functools
import locale
import logging
import math
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot, QTimer, Qt)
import re
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class OutOfRangeError(ValueError):
    pass


class NotFoundError(Exception):
    pass


bitstruct_unpack = functools.lru_cache(10000)(bitstruct.unpack)


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
        if self.comment is None:
            self.comment = ''
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
            self.multiplex = True
        else:
            self.multiplex = signal._multiplex # {NoneType} None

        self.name = signal._name # {str} 'Enable_command'
        # self._receiver = signal._receiver # {str} ''
        self.signal_size = int(signal._signalsize) # {int} 2
        self.start_bit = int(signal.getStartbit()) # {int} 0
        self.ordering_start_bit = signal.getStartbit(bitNumbering=True, startLittle=True)
        self.unit = signal._unit # {str} ''
        self.enumeration = {int(k): v for k, v in signal._values.items()} # {dict} {'0': 'Disable', '2': 'Error', '1': 'Enable', '3': 'N/A'}
        self.signed = signal._is_signed
        if self.multiplex is True:
            self.signed = False
        self.float = signal._is_float

        self._format = None

        self.value = None
        self.scaled_value = None
        self.full_string = None
        self.short_string = None
        self.enumeration_text = None

        self.frame = frame
        # TODO: put this into the frame!
        self.frame.signals.append(self)

        self.enumeration_format_re = {'re': '^\[(\d+)\]',
                                      'format': '[{v}] {s}',
                                      'no_value_format': '{s}'}

        # TODO: make this configurable in the .sym?
        self.secret = self.name == 'FactoryAccess'

        self.decimal_places = None

        self._format = None

        if connect is not None:
            self.connect(connect)

    def __str__(self):
        return '{name}: sb:{start_bit}, osb:{ordering_start_bit}, len:{length}'.format(
            name=self.name,
            start_bit=self.start_bit,
            ordering_start_bit=self.ordering_start_bit,
            length=self.signal_size
        )

    def to_human(self, value):
        return self.offset + (value * float(self.factor))

    def from_human(self, value):
        return round((value - self.offset) / self.factor)

    def get_human_value(self, for_file=False):
        # TODO: handle offset
        if self.value is None:
            return None

        value = self.to_human(self.value)

        return self.format_float(value, for_file=for_file)

    def set_human_value(self, raw_value, force=False, check_range=False):
        # TODO: handle offset
        locale.setlocale(locale.LC_ALL, '')

        if isinstance(raw_value, str):
            enumeration_strings = self.enumeration_strings()
            if len(enumeration_strings) > 0:
                try:
                    index = enumeration_strings.index(raw_value)
                except ValueError:
                    index = int(raw_value)

                value = float(index)
            elif len(raw_value) == 0:
                value = 0
            else:
                value = locale.atof(raw_value)
        else:
            value = float(raw_value)

        self.set_value(value=self.from_human(value),
                       force=force,
                       check_range=check_range)

    def enumeration_string(self, value, include_value=False):
        format = (self.enumeration_format_re['format']
                  if include_value
                  else self.enumeration_format_re['no_value_format'])

        return format.format(v=value, s=self.enumeration[value])

    def enumeration_strings(self, include_values=False):
        items = list(self.enumeration)
        items.sort()
        items = [self.enumeration_string(i, include_value=include_values)
                 for i in items]

        return items

    def get_decimal_places(self):
        if self.decimal_places is None:
            if self.float:
                # TODO: these signals probably ought to have decimal places
                #       specified in the .sym, but that isn't supported yet
                #       anyways.
                self.decimal_places = 3
            else:
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

    def set_value(self, value, force=False, check_range=False):
        value_parameter = value
        if type(value) is float and math.isnan(value):
            return

        if self.value != value or force:
            # TODO: be careful here, should all be int which is immutable
            #       and therefore safe but...  otherwise a copy would be
            #       needed
            if check_range:
                human_value = self.to_human(value)
                if not self.min <= human_value <= self.max:
                    raise OutOfRangeError('{} not in range [{}, {}]'.format(
                        *[self.format_float(f) for f
                          in (human_value, self.min, self.max)]))
            self.value = value

            try:
                # TODO: CAMPid 94562754956589992752348667
                enum_string = self.enumeration[value]
            except KeyError:
                # TODO: this should be a subclass or something
                if self.name == '__padding__':
                    pass
                elif self.hexadecimal_output:
                    pass
                else:
                    # TODO: CAMPid 9395616283654658598648263423685
                    # TODO: and _offset...

                    self.scaled_value = (
                        self.offset + (float(self.value) * self.factor)
                    )

                    value = self.scaled_value

            self.full_string, self.short_string, self.enumeration_text = (
                self.format_strings(value=value_parameter)
            )

        if value_parameter is None:
            self.value_changed.emit(float('nan'))
        else:
            self.value_changed.emit(value)

    def format_strings(self, value):
        if value is None or (type(value) is float and math.isnan(value)):
            full_string = '-'
            short_string = '-'
            enumeration_text = None
        else:
            enumeration_text = None

            try:
                # TODO: CAMPid 94562754956589992752348667
                enum_string = self.enumeration[value]
                full_string = self.enumeration_format_re['format'].format(
                        s=enum_string, v=value)
                enumeration_text = enum_string
                short_string = enum_string
            except KeyError:
                # TODO: this should be a subclass or something
                if self.name == '__padding__':
                    full_string = '__padding__'
                    short_string = full_string
                elif self.hexadecimal_output:
                    format = '{{:0{}X}}'.format(math.ceil(self.signal_size/math.log2(16)))
                    full_string = format.format(int(value))
                    short_string = full_string
                else:
                    # TODO: CAMPid 9395616283654658598648263423685
                    # TODO: and _offset...

                    scaled_value = (
                        self.offset + (float(value) * self.factor)
                    )

                    full_string = self.format_float(scaled_value)
                    short_string = full_string

                    if self.unit is not None:
                        if len(self.unit) > 0:
                            full_string += ' [{}]'.format(self.unit)

        return full_string, short_string, enumeration_text

    def force_value_changed(self):
        value = self.scaled_value
        if value is None:
            value = 0
        self.value_changed.emit(value)

    def format_float(self, value=None, decimal_places=None, for_file=False):
        if self.secret:
            return '<secret>'

        # TODO: ack fix this since it's getting called with an actual None value...
        if value is None:
            value = self.scaled_value

        if value is None:
            formatted = '-'
        else:
            if decimal_places is None:
                decimal_places = self.get_decimal_places()

            if for_file:
                format = '{{:.{}f}}'.format(self.get_decimal_places())
                formatted = format.format(value)
            else:
                format = '%.{}f'.format(decimal_places)
                formatted = locale_format(format, value)

        return formatted

    def format(self):
        if self._format is None:
            if self.float:
                # TODO: CAMPid 097897541967932453154321546542175421549
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

            self._format = ''.join((
                    '<' if self.little_endian else '>',
                    str(type),
                    str(self.signal_size)
            ))

        return self._format


@functools.lru_cache(10000)
def locale_format(format, value):
    return locale.format(format, value, grouping=True)


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
    send = pyqtSignal(can.Message, 'PyQt_PyObject')

    def __init__(self, frame, multiplex_value=None,
                 signal_class=Signal, set_value_to_default=True,
                 mux_frame=None, parent=None):
        QtCanListener.__init__(self, self.message_received, parent=parent)

        self.mux_frame = mux_frame

        self.id = frame._Id # {int} 16755521
        # self._SignalGroups = frame._SignalGroups # {list} []
        self.size = frame._Size # {int} 8
        # self._Transmitter = frame._Transmitter # {list} []
        # self._attributes = frame._attributes # {dict} {'GenMsgCycleTime': '200'}
        self.cycle_time = frame._attributes.get('GenMsgCycleTime', None)
        self.mux_name = frame._attributes.get('mux_name', None)
        self.comment = frame._comment # {str} 'Operational commands are received by the module via control bits within this message.'
        if self.comment is None:
            self.comment = ''
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

        self.format_str = None
        self.data = None

        self.signals = []
        for signal in frame._signals:
            if signal._comment is not None and '<summary>' in signal._comment:
                continue

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

                if set_value_to_default:
                    neo_signal.set_human_value(
                        offset + (default_value * factor))

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
            self.signals.sort(key=lambda x: x.ordering_start_bit)
            # TODO: get rid of this, yuck
            Matrix_Pad = lambda start_bit, length: canmatrix.Signal(
                name='__padding__',
                startBit=start_bit,
                signalSize=length,
                is_little_endian=0)
            def Matrix_Pad_Fixed(start_bit, length):
                pad = Matrix_Pad(start_bit, length)
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
                startbit = signal.ordering_start_bit
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
        if self.format_str is None:
            self.format_str = ''.join([s.format() for s in self.signals])

        return self.format_str

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

        bsl = []
        for v, signal in zip(reversed(data), reversed(self.signals)):
            p = bitstruct.pack(signal.format(), v)
            a = []
            remaining = signal.signal_size
            for b in p:
                bs_ = '{:08b}'.format(b)
                bits = min(8, remaining)
                a.extend(c for c in reversed(bs_[:bits]))
                remaining -= bits

            bsl.extend(s for s in reversed(a))

        return list(reversed(
            bytearray(int(''.join(b), 2)
                      for b in epyqlib.utils.general.grouper(bsl, 8, '0')
            )
        ))

    def unpack(self, data, report_error=True, only_return=False):
        rx_length = len(data)
        if rx_length != self.size and report_error:
            print('Received message 0x{self.id:08X} with length {rx_length}, expected {self.size}'.format(**locals()))
        else:
            self.pad()

            s = ''.join('{:08b}'.format(b) for b in reversed(data))
            unpacked = []
            end = len(s)
            for signal in self.signals:
                start = end - signal.signal_size
                bs = s[start:end]
                end = start

                mbs = []
                while True:
                    mbs.append(bs[-8:])
                    bs = bs[:-8]
                    if len(bs) == 0:
                        break

                mbs[-1] = mbs[-1].ljust(8, '0')

                bs = (int(b, 2) for b in mbs)

                [up] = bitstruct_unpack(signal.format(), tuple(bs))
                unpacked.append(up)

            if only_return:
                return dict(zip(self.signals, unpacked))

            for s, v in zip(self.signals, unpacked):
                s.set_value(v)

    @pyqtSlot()
    def _send(self, update=False):
        if update:
            self.data = self.pack(self)

        self.send.emit(self.to_message(), self._sent)

    def _sent(self):
        pass

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
        return can.Message(extended_id=self.extended,
                           arbitration_id=self.id,
                           dlc=self.size,
                           data=self.data)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if (msg.arbitration_id == self.id and
                bool(msg.id_type) == self.extended):
            if self.mux_frame is None:
                self.unpack(msg.data)
            elif self.mux_frame is self:
                # print(self, self.name, self.mux_name, self.mux_frame, self.mux_frame.name, self.mux_frame.mux_name)

                unpacked = self.mux_frame.unpack(msg.data, only_return=True)
                mux_signal, = (s for s in unpacked if s.name != '__padding__')

                # TODO: this if added to avoid exceptions temporarily
                if mux_signal.value not in self.multiplex_frames:
                    return
                self.multiplex_frames[mux_signal.value].message_received(msg)
            else:
                self.unpack(msg.data)

    def terminate(self):
        callers = tuple(r for r in self._cyclic_requests)
        for caller in callers:
            self.cyclic_request(caller, None)

        logging.debug('{} terminated'.format(object.__repr__(self)))


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
                if 'GenMsgCycleTime' in frame._attributes:
                    multiplex_frame.addAttribute(
                        'GenMsgCycleTime',
                        frame._attributes['GenMsgCycleTime']
                    )
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
                multiplex_neo_frame.mux_frame = multiplex_neo_frame
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
                    if 'GenMsgCycleTime' in frame._attributes:
                        matrix_frame.addAttribute(
                            'GenMsgCycleTime',
                            frame._attributes['GenMsgCycleTime']
                        )
                    matrix_frame.addAttribute('mux_name', multiplex_name)
                    matrix_frame.addComment(multiplex_signal.comments[int(
                        multiplex_value)])
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

                    neo_frame = frame_class(
                        frame=matrix_frame,
                        mux_frame=multiplex_neo_frame
                    )
                    for signal in neo_frame.signals:
                        if signal.multiplex is True:
                            signal.set_value(int(multiplex_value))
                    frames.append(neo_frame)
                    multiplex_neo_frame.\
                        multiplex_frames[int(multiplex_value)] = neo_frame

        if bus is not None:
            for frame in frames:
                frame.send.connect(bus.send)

        self.frames = frames

    def frame_by_id(self, id):
        found = (
            f for f in self.frames
            if f.id == id and f.mux_name is None
        )

        try:
            frame, = found
        except ValueError:
            return None

        return frame

    def frame_by_name(self, name):
        try:
            return next(f for f in self.frames if f.name == name)
        except StopIteration:
            return None

    def signal_by_path(self, *elements):
        i = iter(elements)

        def get_next(i):
            try:
                return next(i)
            except StopIteration as e:
                raise NotFoundError(', '.join(elements)) from e

        element = get_next(i)

        frame = self.frame_by_name(element)

        if frame is None:
            raise NotFoundError(', '.join(elements))

        if hasattr(frame, 'multiplex_frames'):
            element = get_next(i)

            frames = (
                f for f in frame.multiplex_frames.values()
                if f.mux_name == element
            )
            try:
                [frame] = frames
            except ValueError:
                raise NotFoundError(', '.join(elements))

        element = get_next(i)

        signal = frame.signal_by_name(element)
        if signal is None:
            raise NotFoundError(', '.join(elements))

        return signal

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
                return (base_frame, None)

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

    def terminate(self):
        for frame in self.frames:
            frame.terminate()

        logging.debug('epyqlib.canneo.bitstruct_unpack(): {}'.format(
                      bitstruct_unpack.cache_info()))
        logging.debug('{} terminated'.format(object.__repr__(self)))


def format_identifier(identifier, extended):
    f = '0x{{:0{}X}}'

    if extended:
        f = f.format(8)
    else:
        f = f.format(3)

    return f.format(identifier)

def format_data(data):
    return ' '.join(['{:02X}'.format(byte) for byte in data])
