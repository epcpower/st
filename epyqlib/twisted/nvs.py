import enum
import logging
import sys
import twisted.internet.defer
import twisted.protocols.policies

__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger(__name__)


class RequestTimeoutError(TimeoutError):
    pass


@enum.unique
class State(enum.Enum):
    idle = 0
    reading = 1
    writing = 2


class Protocol(twisted.protocols.policies.TimeoutMixin):
    def __init__(self, tx_id=0x0CFFAA41, rx_id=0x1CFFA9F7, extended=True,
                 timeout=1):
        self._deferred = None

        self._state = State.idle
        self._previous_state = self._state

        self._active = False

        self._tx_id = tx_id
        self._rx_id = rx_id
        self._extended = extended

        self._request_memory = None
        self._timeout = timeout

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        logger.debug('Entering state {}'.format(new_state))
        self._previous_state = self._state
        self._state = new_state

    def makeConnection(self, transport):
        self._transport = transport
        logger.debug('Protocol.makeConnection(): {}'.format(transport))

    def _new_deferred(self):
        self._deferred = twisted.internet.defer.Deferred()

    def _start_transaction(self):
        if self._active:
            raise Exception('Protocol is already active')

        self._active = True

        self._new_deferred()

    def read(self, nv_signal):
        self._start_transaction()

        read_write, = (k for k, v
                       in nv_signal.frame.read_write.enumeration.items()
                       if v == 'Read')

        nv_signal.frame.read_write.set_data(read_write)
        nv_signal.frame.update_from_signals()

        self._transport.write_passive(nv_signal.frame.to_message())
        self.setTimeout(self._timeout)

        self._request_memory = nv_signal.status_signal

        return self._deferred

    def write(self, nv_signal):
        self._start_transaction()

        read_write, = (k for k, v
                       in nv_signal.frame.read_write.enumeration.items()
                       if v == 'Write')

        nv_signal.frame.read_write.set_data(read_write)
        nv_signal.frame.update_from_signals()

        self._transport.write_passive(nv_signal.frame.to_message())
        self.setTimeout(self._timeout)

        self._request_memory = nv_signal.status_signal

        return self._deferred

    def dataReceived(self, msg):
        logger.debug('Message received: {}'.format(msg))
        if not (msg.arbitration_id == self._rx_id and
                        bool(msg.id_type) == self._extended):
            return

        # TODO: check the mux value!
        if not self._active:
            return

        self.setTimeout(None)

        status_signal = self._request_memory

        signals = status_signal.frame.unpack(msg.data, only_return=True)

        # TODO: check mux and read vs. write

        raw_value = signals[status_signal]
        value = status_signal.to_human(value=raw_value)

        self.callback(value)

    def timeoutConnection(self):
        message = 'Protocol timed out while in state: {}'.format(self.state)
        logger.debug(message)
        self._active = False
        if self._previous_state in [State.idle]:
            self.state = self._previous_state
        self._deferred.errback(RequestTimeoutError(message))

    def callback(self, payload):
        self._active = False
        logger.debug('calling back for {}'.format(self._deferred))
        self._deferred.callback(payload)

    def errback(self, payload):
        self._active = False
        logger.debug('erring back for {}'.format(self._deferred))
        logger.debug('with payload {}'.format(payload))
        self._deferred.errback(payload)

    def cancel(self):
        self._active = False
        self.setTimeout(None)
        self._deferred.cancel()
