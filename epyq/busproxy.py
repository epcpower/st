#!/usr/bin/env python3

# TODO: get some docstrings in here!

import can
import can.interfaces.pcan
import time

from epyq.canneo import QtCanListener
from PyQt5.QtCore import QObject, pyqtSignal

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class BusProxy(QObject):
    went_offline = pyqtSignal()

    def __init__(self, bus=None, timeout=0.1, parent=None):
        QObject.__init__(self, parent=parent)

        self.timeout = timeout
        self.notifier = NotifierProxy(self)
        self.real_notifier = None
        self.bus = None
        self.set_bus(bus)

    def send(self, msg):
        if self.bus is not None:
            # TODO: I would use message=message (or msg=msg) but:
            #       https://bitbucket.org/hardbyte/python-can/issues/52/inconsistent-send-signatures
            sent = self.bus.send(msg)

            self.verify_bus_ok()

            # TODO: since send() doesn't always report failures this won't either
            #       fix that
            return sent

        return False

    def verify_bus_ok(self):
        if self.bus is None:
            # No bus, nothing to go wrong with it... ?
            ok = True
        else:
            if hasattr(self.bus, 'StatusOk'):
                ok = self.bus.StatusOk()

                if not ok:
                    self.set_bus()
            else:
                try:
                    ok = self.bus.verify_bus_ok()
                except AttributeError:
                    # TODO: support socketcan
                    ok = True

        return ok

    def shutdown(self):
        pass

    def flash(self):
        if self.bus is not None:
            return self.bus.flash()

    def set_bus(self, bus=None):
        was_online = self.bus is not None

        if was_online:
            if isinstance(self.bus, can.BusABC):
                self.real_notifier.running.clear()
                time.sleep(1.1 * self.timeout)
            else:
                self.bus.notifier.remove(self.notifier)
            self.bus.shutdown()
        self.bus = bus

        if self.bus is not None:
            if isinstance(self.bus, can.BusABC):
                self.real_notifier = can.Notifier(
                    bus=self.bus,
                    listeners=[self.notifier],
                    timeout=self.timeout)
            else:
                self.bus.notifier.add(self.notifier)
                self.real_notifier = None
        else:
            self.real_notifier = None

        self.reset()

        if was_online and self.bus is None:
            self.went_offline.emit()

    def reset(self):
        if self.bus is not None:
            if isinstance(self.bus, can.interfaces.pcan.PcanBus):
                self.bus.Reset()
                # TODO: do this a better way
                # Give PCAN a chance to actually reset and avoid immediate
                # send failures
                time.sleep(0.500)
            else:
                try:
                    self.bus.reset()
                except AttributeError:
                    # TODO: support socketcan
                    pass

class NotifierProxy(QtCanListener):
    def __init__(self, bus, listeners=[], parent=None):
        QtCanListener.__init__(self, receiver=self.message_received, parent=parent)

        self.listeners = set(listeners)

    def message_received(self, message):
        for listener in self.listeners:
            listener.message_received_signal.emit(message)

    def add(self, listener):
        self.listeners.add(listener)

    def discard(self, listener):
        self.listeners.discard(listener)

    def remove(self, listener):
        self.listeners.remove(listener)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
