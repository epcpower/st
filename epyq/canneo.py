import bitstruct
import can
from canmatrix import canmatrix
import copy
import functools
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
        self.little_endian = signal._byteorder # {int} 0
        self.comment = signal._comment # {str} 'Run command.  When set to a value of \\'Enable\\', causes transition to grid forming or grid following mode depending on whether AC power is detected.  Must be set to \\'Disable\\' to leave POR or FAULTED state.'
        # TODO: maybe not use a string, but used to help with decimal places
        self.factor = {
            str: None,
            float: None
        }
        self.factor[str] = signal._factor # {str} '1'
        try:
            self.factor[float] = float(signal._factor) # {str} '1'
        except ValueError:
            pass
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

        self.multiplex = signal._multiplex # {NoneType} None
        self.name = signal._name # {str} 'Enable_command'
        # self._receiver = signal._receiver # {str} ''
        self.signal_size = int(signal._signalsize) # {int} 2
        self.start_bit = int(signal.getMsbReverseStartbit()) # {int} 0
        self.unit = signal._unit # {str} ''
        self.enumeration = {int(k): v for k, v in signal._values.items()} # {dict} {'0': 'Disable', '2': 'Error', '1': 'Enable', '3': 'N/A'}
        if signal._valuetype in ['-']:
            self.signed = True
        elif signal._valuetype in ['+', None]:
            self.signed = False
        else:
            raise ValueError("Expected '+' or '-' but got '{}'"
                             .format(signal._valuetype))

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

        value = self.value * float(self.factor)

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

        value /= self.factor[float]
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
            factor_str = self.factor[str].rstrip('0.')
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
                # TODO: CAMPid 94562754956589992752348667
                enum_string = self.enumeration[value]
                self.full_string = self.enumeration_format_re['format'].format(
                        s=enum_string, v=value)
            except KeyError:
                # TODO: this should be a subclass or something
                if self.name == '__padding__':
                    self.full_string = '__padding__'
                else:
                    # TODO: CAMPid 9395616283654658598648263423685
                    # TODO: and _offset...

                    self.scaled_value = float(self.value) * self.factor[float]

                    self.full_string = self.format_float(self.scaled_value)

                    if self.unit is not None:
                        if len(self.unit) > 0:
                            self.full_string += ' [{}]'.format(self.unit)

                    value = self.scaled_value

            self.value_changed.emit(value)

    def format_float(self, value=None):
        if value is None:
            value = self.scaled_value
        return '{{:.{}f}}'.format(self.get_decimal_places()).format(value)

    def format(self):
        return '{}{}{}'.format(
                '<' if self.little_endian else '>',
                's' if self.signed else 'u',
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
        self.timer = QTimer()
        _update_and_send = functools.partial(self._send, update=True)
        self.timer.timeout.connect(_update_and_send)

        self.signals = []
        for signal in frame._signals:
            if (multiplex_value is None or
                        str(signal._multiplex) == multiplex_value):
                neo_signal = signal_class(signal=signal, frame=self)

                factor = neo_signal.factor[float]
                if factor is None:
                    factor = 1

                default_value = neo_signal.default_value
                if default_value is None:
                    default_value = 0

                neo_signal.set_human_value(default_value * factor)

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
                startbit=start_bit,
                signalsize=length,
                byteorder=0,
                valuetype=None,
                factor=None,
                offset=None,
                min=None,
                max=None,
                unit=None,
                multiplex=None)
            def Matrix_Pad_Fixed(start_bit, length):
                pad = Matrix_Pad(start_bit, length)
                pad.setMsbReverseStartbit(start_bit)
                return pad
            Pad = lambda start_bit, length: Signal(
                signal=Matrix_Pad_Fixed(start_bit, length),
                frame=self
            )
            # TODO: 1 or 0, which is the first bit per canmatrix?
            bit = 0
            # pad for unused bits
            unpadded_signals = list(self.signals)
            for signal in unpadded_signals:
                startbit = signal.start_bit
                if startbit < bit:
                    raise Exception('too far ahead!')
                padding = startbit - bit
                if padding:
                    pad = Pad(bit, padding)
                    # TODO: yucky to add out here
                    pad.start_bit = bit
                    bit += pad.signal_size
                bit += signal.signal_size
            # TODO: 1 or 0, which is the first bit per canmatrix?
            padding = (self.size * 8) - bit
            if padding < 0:
                # TODO: fix the common issue so the exception can be used
                # raise Exception('frame too long!')
                print('Frame too long!  (but this is expected for now since the DBC seems wrong)')
            elif padding > 0:
                Pad(bit, padding)

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

    def unpack(self, data):
        rx_length = len(data)
        if rx_length != self.size:
            print('Received message length {rx_length} != {self.frame._Size} received'.format(**locals()))
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


class Neo:
    def __init__(self, matrix, frame_class=Frame, signal_class=Signal, bus=None):
        frames = []

        for frame in matrix._fl._list:
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
                        multiplex_signal._multiplex)
                multiplex_frame.addSignal(matrix_signal)
                multiplex_neo_frame = frame_class(frame=multiplex_frame)
                frames.append(multiplex_neo_frame)
                # neo_signal = signal_class(signal=matrix_signal, frame=multiplex_neo_frame)

                for signal in multiplex_neo_frame.signals:
                    if signal.multiplex is None:
                        neo_signal = signal

                multiplex_neo_frame.multiplex_signal = neo_signal
                # neo_frame.multiplex_frame = multiplex_neo_frame
                multiplex_neo_frame.multiplex_signal = neo_signal
                multiplex_neo_frame.multiplex_frames = {}

                for multiplex_value, multiplex_name in multiplex_signal._values.items():
                    # For each multiplexed frame, make a frame with
                    # just those signals.
                    matrix_frame = canmatrix.Frame(
                            frame._Id,
                            frame._name,
                            frame._Size,
                            frame._Transmitter)
                    matrix_frame._extended = frame._extended
                    matrix_frame.addAttribute('mux_name', multiplex_name)
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
                            multiplex_signal._multiplex)
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
            base_frame.unpack(message.data)
            multiplex_value = base_frame.multiplex_signal.value
            try:
                frame = base_frame.multiplex_frames[multiplex_value]
            except KeyError:
                return (None, None)

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
