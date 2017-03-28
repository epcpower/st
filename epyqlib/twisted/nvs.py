import enum
import logging
import queue

import attr
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


@attr.s
class Request:
    read = attr.ib()
    signal = attr.ib()
    deferred = attr.ib()


class Protocol(twisted.protocols.policies.TimeoutMixin):
    def __init__(self, timeout=1):
        self._deferred = None

        self._state = State.idle
        self._previous_state = self._state

        self._active = False

        self._request_memory = None
        self._timeout = timeout

        self.requests = queue.Queue()

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

    def _start_transaction(self):
        if self._active:
            raise Exception('Protocol is already active')

        self._active = True

    def _transaction_over(self):
        import twisted.internet
        twisted.internet.reactor.callLater(0.02, self._transaction_over_after_delay)

    def _transaction_over_after_delay(self):
        self._active = False
        self._get()

    def read(self, nv_signal):
        return self._read_write_request(nv_signal=nv_signal, read=True)

    def write(self, nv_signal):
        return self._read_write_request(nv_signal=nv_signal, read=False)

    def _read_write_request(self, nv_signal, read):
        deferred = twisted.internet.defer.Deferred()
        self._put(Request(
            read=read,
            signal=nv_signal,
            deferred=deferred
        ))

        return deferred

    def _put(self, request):
        self.requests.put(request)
        self._get()

    def _get(self):
        if not self._active:
            try:
                request = self.requests.get(block=False)
            except queue.Empty:
                pass
            else:
                self._deferred = request.deferred
                self._read_write(
                    nv_signal=request.signal,
                    read=request.read
                )

    def _read_write(self, nv_signal, read):
        self._start_transaction()

        read_write, = (k for k, v
                       in nv_signal.frame.read_write.enumeration.items()
                       if v == ('Read' if read else 'Write'))

        nv_signal.frame.read_write.set_data(read_write)
        nv_signal.frame.update_from_signals()

        self._transport.write_passive(nv_signal.frame.to_message())
        self.setTimeout(self._timeout)

        self._request_memory = nv_signal.status_signal

        return self._deferred

    def dataReceived(self, msg):

        logger.debug('Message received: {}'.format(msg))
        if not self._active:
            return

        status_signal = self._request_memory

        if status_signal is None:
            return

        if not (msg.arbitration_id == status_signal.frame.id and
                        bool(msg.id_type) == status_signal.frame.extended):
            return

        signals = status_signal.frame.unpack(msg.data, only_return=True)

        mux = status_signal.set_signal.frame.mux.value
        response_mux_value, = (v for k, v in signals.items() if k.name == 'ParameterResponse_MUX')
        if response_mux_value != mux:
            return
        response_read_write_value, = (v for k, v in signals.items() if k.name
                                      == 'ReadParam_status')
        if response_read_write_value != \
                status_signal.set_signal.frame.read_write.value:
            return

        self.setTimeout(None)

        raw_value = signals[status_signal]
        value = status_signal.to_human(value=raw_value)

        self.callback(value)

    def timeoutConnection(self):
        message = 'Protocol timed out while in state: {}'.format(self.state)
        logger.debug(message)
        if self._previous_state in [State.idle]:
            self.state = self._previous_state
        self._transaction_over()
        self._deferred.errback(RequestTimeoutError(message))

    def callback(self, payload):
        self._transaction_over()
        logger.debug('calling back for {}'.format(self._deferred))
        self._deferred.callback(payload)

    def errback(self, payload):
        self._transaction_over()
        logger.debug('erring back for {}'.format(self._deferred))
        logger.debug('with payload {}'.format(payload))
        self._deferred.errback(payload)

    def cancel(self):
        self.setTimeout(None)
        self._transaction_over()
        self._deferred.cancel()
