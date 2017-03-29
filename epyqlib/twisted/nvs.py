import enum
import logging
import queue

import attr
import twisted.internet.defer
import twisted.protocols.policies

import epyqlib.utils.general

__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger(__name__)


class RequestTimeoutError(TimeoutError):
    pass


class ReadOnlyError(Exception):
    pass


@enum.unique
class State(enum.Enum):
    idle = 0
    reading = 1
    writing = 2


@enum.unique
class Priority(enum.IntEnum):
    user = 0
    background = 1


@attr.s
class Request:
    priority = attr.ib()
    read = attr.ib(cmp=False)
    signal = attr.ib(cmp=False)
    deferred = attr.ib(cmp=False)
    passive = attr.ib(cmp=False)


class Protocol(twisted.protocols.policies.TimeoutMixin):
    def __init__(self, timeout=1):
        self._deferred = None

        self._state = State.idle
        self._previous_state = self._state

        self._active = False

        self._request_memory = None
        self._timeout = timeout

        self.requests = queue.PriorityQueue()

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
        d = self._deferred
        self._deferred = None
        self.state = State.idle
        return d

    def _transaction_over_after_delay(self):
        self._active = False
        self._get()

    def read(self, nv_signal, priority=Priority.background, passive=False):
        return self._read_write_request(
            nv_signal=nv_signal,
            read=True,
            priority=priority,
            passive=passive
        )

    def write(self, nv_signal, priority=Priority.background, passive=False,
              ignore_read_only=False):
        if nv_signal.frame.read_write.min > 0:
            if ignore_read_only:
                return
            else:
                raise ReadOnlyError()

        return self._read_write_request(
            nv_signal=nv_signal,
            read=False,
            priority=priority,
            passive=passive
        )

    def _read_write_request(self, nv_signal, read, priority, passive):
        deferred = twisted.internet.defer.Deferred()
        self._put(Request(
            read=read,
            signal=nv_signal,
            deferred=deferred,
            priority=priority,
            passive=passive
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
                    read=request.read,
                    passive=request.passive
                )

    def _read_write(self, nv_signal, read, passive):
        self._start_transaction()
        self.state = State.reading if read else State.writing

        read_write, = (k for k, v
                       in nv_signal.frame.read_write.enumeration.items()
                       if v == ('Read' if read else 'Write'))

        nv_signal.frame.read_write.set_data(read_write)
        nv_signal.frame.update_from_signals()

        if passive:
            write = self._transport.write_passive
        else:
            write = self._transport.write

        write(nv_signal.frame.to_message())
        self.setTimeout(self._timeout)

        self._request_memory = nv_signal.status_signal

    def dataReceived(self, msg):

        logger.debug('Message received: {}'.format(msg))
        if not self._active:
            return

        if self._deferred is None:
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
        status_signal = self._request_memory
        message = 'Protocol timed out while in state {} handling ' \
                  '{} : {}'.format(
            self.state,
            status_signal.frame.mux_name,
            status_signal.name
        )
        logger.debug(message)
        if self._previous_state in [State.idle]:
            self.state = self._previous_state
        deferred = self._transaction_over()
        deferred.errback(RequestTimeoutError(message))

    def callback(self, payload):
        deferred = self._transaction_over()
        logger.debug('calling back for {}'.format(deferred))
        deferred.callback(payload)

    def errback(self, payload):
        deferred = self._transaction_over()
        logger.debug('erring back for {}'.format(deferred))
        logger.debug('with payload {}'.format(payload))
        deferred.errback(payload)

    def cancel(self):
        self.setTimeout(None)
        deferred = self._transaction_over()
        deferred.cancel()
