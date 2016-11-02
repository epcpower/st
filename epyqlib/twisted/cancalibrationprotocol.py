import logging
import can
import collections
import enum
import epyqlib.busproxy
import epyqlib.canneo
import functools
import os
import signal
import sys
import twisted.internet.defer
import twisted.protocols.policies

from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication


logger = logging.getLogger()


def main():
    app = QApplication(sys.argv)

    real_bus = can.interface.Bus(bustype='socketcan', channel='can0')
    bus = epyqlib.busproxy.BusProxy(bus=real_bus)
    handler = Handler(bus=bus)
    bus.notifier.add(handler)

    QTimer.singleShot(0, handler.connect)

    return app.exec_()


class HandlerBusy(RuntimeError):
    pass

class HandlerUnknownState(RuntimeError):
    pass

class UnexpectedMessageReceived(ValueError):
    pass


bootloader_can_id = 0x0B081880


@enum.unique
class HandlerState(enum.Enum):
    idle = 0
    connecting = 1
    connected = 2
    disconnecting = 3


class Handler(twisted.protocols.policies.TimeoutMixin):
    def __init__(self, id=bootloader_can_id, extended=True, parent=None):
        self._deferred = None
        self._active = False
        self._transport = None

        self._id = id
        self._extended = extended

        self._send_counter = 0

        self._state = HandlerState.idle

        self._remaining_retries = 0

    def makeConnection(self, transport):
        self._transport = transport
        logger.debug('Handler.makeConnection(): {}'.format(transport))

    def connect(self):
        if self._active:
            raise Exception('self._active is True')

        self._deferred = twisted.internet.defer.Deferred()

        if self._state is not HandlerState.idle:
            self.errback(HandlerBusy(
                'Connect requested while {}'.format(self._state.name)))
            return

        packet = HostCommand(code=CommandCode.connect)
        self._send(packet)

        self._state = HandlerState.connecting

        return self._deferred

    def disconnect(self):
        if self._active:
            raise Exception('self._active is True')

        self._deferred = twisted.internet.defer.Deferred()

        if self._state is not HandlerState.connected:
            self.errback(HandlerBusy(
                'Disconnect requested while {}'.format(self._state.name)))
            return

        packet = HostCommand(code=CommandCode.disconnect)
        self._send(packet)

        self._state = HandlerState.disconnecting

        logger.debug('disconnecting')
        return self._deferred


    def _send(self, packet, timeout=1):
        packet.command_counter = self._send_counter

        if self._send_counter < 255:
            self._send_counter += 1
        else:
            self._send_counter = 0

        self._transport.write(packet)

        if timeout > 0:
            self.setTimeout(timeout)
        else:
            self.resetTimeout()

    def dataReceived(self, msg):
        if not (msg.arbitration_id == self._id and
                    bool(msg.id_type) == self._extended):
            return

        if self._active:
            raise Exception('self._active is False')

        self.setTimeout(None)

        packet = Packet.from_message(message=msg)

        if not isinstance(packet, BootloaderReply):
            self.errback(UnexpectedMessageReceived(
                'Not a bootloader reply: {}'.format(packet)))
            return

        logger.debug('packet received: {}'.format(packet.command_return_code.name))

        if self._state is HandlerState.connecting:
            if packet.command_return_code is not CommandStatus.acknowledge:
                self.errback(UnexpectedMessageReceived(
                    'Bootloader should ack when trying to connect, instead: {}'
                        .format(packet)))
                return

            logger.debug('Bootloader version: {major}.{minor}'.format(
                major=packet.payload[0],
                minor=packet.payload[1]
            ))

            dsp_code = (int(packet.payload[2]) << 8) + int(packet.payload[3])

            logger.debug('DSP Part ID: {}'.format(DspCode(dsp_code).name))

            self._state = HandlerState.connected
            self.callback('successfully connected')
        elif self._state is HandlerState.disconnecting:
            if packet.command_return_code is not CommandStatus.acknowledge:
                self.errback(UnexpectedMessageReceived(
                    'Bootloader should ack when trying to disconnect, instead: {}'
                        .format(packet)))
                return

            self._state = HandlerState.idle
            self.callback('successfully disconnected')
        else:
            self.errback(HandlerUnknownState(
                'Handler in unknown state: {}'.format(self._state)))
            return

    def timeoutConnection(self):
        raise Exception(
            'Handler timed out while in state: {}'.format(self._state))

    def callback(self, payload):
        self._active = False
        logger.debug('calling back')
        self._deferred.callback(payload)

    def errback(self, payload):
        self._active = False
        logger.debug('erring back')
        self._deferred.errback(payload)


def crc(bytes):
    crc = 0xFFFF

    for byte in bytes:
        crc = crc ^ (byte & 0x00FF)

        for _ in range(8):
            if (crc & 0x0001) != 0:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = (crc >> 1)

    return crc


class IdentifierTypeError(ValueError):
    pass


class PayloadLengthError(ValueError):
    pass


class MessageLengthError(ValueError):
    pass


class Packet(can.Message):
    def __init__(self, counter_index, payload_start, extended_id=True,
                 arbitration_id=bootloader_can_id, dlc=8, *args, **kwargs):
        # TODO: avoid repetition of required values
        # TODO: block changing of required values
        if not extended_id:
            raise IdentifierTypeError('Identifier type must be set to extended')

        if dlc != 8:
            raise MessageLengthError(
                'Message length must be 8 but is {}'.format(dlc))

        kwargs.setdefault('data', [0] * dlc)

        super().__init__(extended_id=extended_id,
                         arbitration_id=arbitration_id, dlc=dlc,
                         *args, **kwargs)

        self._counter_index = counter_index
        self._payload_start = payload_start

    @classmethod
    def from_message(cls, message):
        if message.data[0] == 0xFF:
            c = BootloaderReply
        else:
            c = HostCommand

        return c(
            code=None,
            timestamp=message.timestamp,
            is_remote_frame=message.is_remote_frame,
            extended_id=message.id_type,
            is_error_frame=message.is_error_frame,
            arbitration_id=message.arbitration_id,
            dlc=message.dlc,
            data=message.data
        )

    @property
    def payload(self):
        return self.data[self._payload_start:]


    @payload.setter
    def payload(self, payload):
        maximum_payload = self.dlc - self._payload_start
        if len(payload) > maximum_payload:
            raise PayloadLengthError(
                'Maximum payload length exceeded: {actual} > {maximum}'.format(
                    actual=len(payload),
                    maximum=maximum_payload
                ))

        payload += [0] * ((self.dlc - self._payload_start) - len(payload))
        self.data[self._payload_start:] = payload

    @property
    def command_counter(self):
        return self.data[self._counter_index]


    @command_counter.setter
    def command_counter(self, counter):
        self.data[self._counter_index] = int(counter)


class HostCommand(Packet):
    def __init__(self, code, *args, **kwargs):
        super().__init__(counter_index=1, payload_start=2, *args, **kwargs)

        if code is not None:
            self.command_code = code

    @property
    def command_code(self):
        return CommandCode(self.data[0])

    @command_code.setter
    def command_code(self, code):
        self.data[0] = int(code)


class BootloaderReply(Packet):
    def __init__(self, code, *args, **kwargs):
        super().__init__(counter_index=2, payload_start=3, *args, **kwargs)

        if code is not None:
            self.command_return_code = code

    @property
    def command_return_code(self):
        return CommandStatus(self.data[1])

    @command_return_code.setter
    def command_return_code(self, code):
        self.data[1] = int(code)


@enum.unique
class CommandCode(enum.IntEnum):
    connect = 0x01
    set_mta = 0x02
    download = 0x03
    disconnect = 0x07
    build_checksum = 0x0E
    clear_memory = 0x10
    unlock = 0x13
    action_service = 0x21
    download_6 = 0x23

    # def __getattr__(self, name):
    #     return getattr(_command_code_properties[self], name)

    @property
    def timeout(self):
        return _command_code_properties[self].timeout


CommandCodeProperties = collections.namedtuple(
    'CommandCodeProperties',
    [
        'timeout'
    ]
)


_command_code_properties = {
    CommandCode.connect: CommandCodeProperties(timeout=1000),
    CommandCode.set_mta: CommandCodeProperties(timeout=1000),
    CommandCode.download: CommandCodeProperties(timeout=1000),
    CommandCode.disconnect: CommandCodeProperties(timeout=1000),
    CommandCode.build_checksum: CommandCodeProperties(timeout=1000),
    CommandCode.clear_memory: CommandCodeProperties(timeout=30000),
    CommandCode.unlock: CommandCodeProperties(timeout=1000),
    CommandCode.action_service: CommandCodeProperties(timeout=1000),
    CommandCode.download_6: CommandCodeProperties(timeout=1000)
}


@enum.unique
class DspCode(enum.IntEnum):
    _2801 = 0x002C
    _2802 = 0x0024
    _2806 = 0x0034
    _2808 = 0x003C
    _2809 = 0x00FE
    _28232 = 0x00E6
    _28234 = 0x00E7
    _28235 = 0x00E8
    _28332 = 0x00ED
    _28334 = 0x00EE
    _28335 = 0x00EF
    _28069PZP = 0x009E
    _28069UPZ = 0x009F
    _28069PFP = 0x009C
    _28069UPFP = 0x009D


@enum.unique
class ErrorCategory(enum.Enum):
    timeout = -1
    c0 = 0
    c1 = 1
    c2 = 2
    c3 = 3

    @property
    def description(self):
        return _error_category_properties[self].description

    @property
    def action(self):
        return _error_category_properties[self].action

    @property
    def retries(self):
        return _error_category_properties[self].retries


ErrorCategoryProperties = collections.namedtuple(
    'ErrorCategoryProperties',
    [
        'description',
        'action',
        'retries'
    ]
)


_error_category_properties = {
    ErrorCategory.timeout: ErrorCategoryProperties(
        description='No handshake message',
        action='retry',
        retries=2
    ),
    ErrorCategory.c0: ErrorCategoryProperties(
        description='Warning',
        action=None,
        retries=None
    ),
    ErrorCategory.c1: ErrorCategoryProperties(
        description='Spurious (comm. Error, busy, ..)',
        action='Wait (ACK or timeout)',
        retries=2
    ),
    ErrorCategory.c2: ErrorCategoryProperties(
        description='Resolvable (temp, power loss, ..)',
        action='reinitialize',
        retries=1
    ),
    ErrorCategory.c3: ErrorCategoryProperties(
        description='Unresolvable (setup, overload, ..)',
        action='terminate',
        retries=None
    )
}


@enum.unique
class CommandStatus(enum.IntEnum):
    acknowledge = 0x00 # no error
    processor_busy = 0x10
    unknown_command = 0x30
    command_syntax = 0x31
    parameters_out_of_range = 0x32
    access_denied = 0x33
    access_locked = 0x35
    resource_function_unavailable = 0x36
    operational_failure = 0x7F

    @property
    def error_category(self):
        return _command_status_properties[self].error_category

    @property
    def state_transition_to(self):
        return _command_status_properties[self].state_transition_to


CommandStatusProperties = collections.namedtuple(
    'CommandStatusProperties',
    [
        'error_category',
        'state_transition_to'
    ]
)


_command_status_properties = {
    CommandStatus.acknowledge: CommandStatusProperties(
        error_category=None,
        state_transition_to=None
    ),
    CommandStatus.processor_busy: CommandStatusProperties(
        error_category=ErrorCategory.c1,
        state_transition_to='Fault'
    ),
    CommandStatus.unknown_command: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
    CommandStatus.command_syntax: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
    CommandStatus.parameters_out_of_range: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
    CommandStatus.access_denied: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
    CommandStatus.access_locked: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
    CommandStatus.resource_function_unavailable: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
    CommandStatus.operational_failure: CommandStatusProperties(
        error_category=ErrorCategory.c3,
        state_transition_to='Fault'
    ),
}

if __name__ == '__main__':
    import sys
    import traceback

    def excepthook(excType, excValue, tracebackobj):
        logger.debug('Uncaught exception hooked:')
        traceback.print_exception(excType, excType, tracebackobj)

    sys.excepthook = excepthook
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(main())
