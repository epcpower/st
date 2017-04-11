import collections

import attr
import twisted.internet.task

import epyqlib.utils.twisted


@attr.s
class Request:
    f = attr.ib()
    period = attr.ib()


@attr.s
class Element:
    loop = attr.ib()
    period = attr.ib()


@attr.s
class Set:
    requests = attr.ib(init=False,
                       default=attr.Factory(lambda: collections.defaultdict(
                           dict)))
    periods = attr.ib(init=False, default=attr.Factory(dict))
    loops = attr.ib(init=False, default=attr.Factory(dict))

    def add_request(self, key, request):
        self.requests[request.f][key] = request

        self._update_period(request.f)

    def remove_request(self, key, request):
        self.requests[request.f].pop(key)

        self._update_period(request.f)

    def _update_period(self, f):
        minimum_period = min(r.period for r in self.requests[f].values())

        if f not in self.loops:
            self.loops[f] = Element(
                loop=twisted.internet.task.LoopingCall(f),
                period=minimum_period
            )

            _start_loop(self.loops[f].loop, self.loops[f].period)

        if minimum_period != self.loops[f].period:
            self.loops[f].loop.stop()

            self.loops[f] = Element(
                loop=twisted.internet.task.LoopingCall(f),
                period=minimum_period
            )

            _start_loop(self.loops[f].loop, self.loops[f].period)

    def stop(self):
        for element in self.loops.values():
            if element.loop.running:
                element.loop.stop()

    def start(self):
        for element in self.loops.values():
            if not element.loop.running:
                _start_loop(element.loop, element.period)


def _start_loop(loop, period):
    loop_deferred = loop.start(period)
    loop_deferred.addErrback(epyqlib.utils.twisted.errbackhook)


if __name__ == '__main__':
    # TODO: move this to a unit test and actually check it's result
    #       automatically
    import twisted.internet.reactor

    a = lambda: print('a')
    b = lambda: print('b')
    requests = (
        (1, Request(f=a, period=0.5)),
        (0, Request(f=a, period=2)),
        (0, Request(f=a, period=1)),
        (0, Request(f=b, period=1)),
    )

    looping_set = Set()
    for key, request in requests:
        print('Adding: {}: {}'.format(key, request))
        looping_set.add_request(key=key, request=request)

    reactor = twisted.internet.reactor
    reactor.callLater(5, reactor.stop)
    reactor.run()
