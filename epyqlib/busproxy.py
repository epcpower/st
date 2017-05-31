#!/usr/bin/env python3

# TODO: get some docstrings in here!

import can
import can.interfaces.pcan
import logging
import time

from epyqlib.canneo import QtCanListener
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class BusProxy(QObject):
    went_offline = pyqtSignal()

    def __init__(self, bus=None, timeout=0.1, transmit=True, filters=None,
                 auto_disconnect=True, parent=None):
        QObject.__init__(self, parent=parent)

        self.filters = filters
        self.auto_disconnect = auto_disconnect

        self.timeout = timeout
        self.notifier = NotifierProxy(self)
        self.real_notifier = None
        self.bus = None
        self.set_bus(bus)

        self._transmit = transmit

    @property
    def transmit(self):
        return self._transmit

    @transmit.setter
    def transmit(self, transmit):
        self._transmit = transmit

    def send(self, msg, on_success=None):
        self._send(msg, on_success=on_success)

    def send_passive(self, msg, on_success=None):
        self._send(msg, on_success=on_success, passive=True)

    def _send(self, msg, on_success=None, passive=False):
        if self.bus is not None and (self._transmit or passive):
            # TODO: this (the silly sleep) is really hacky and shouldn't be needed but it seems
            #       to be to keep from forcing socketcan offbus.  the issue
            #       can be recreated with the following snippet.
            # import can
            # import time
            # bus = can.interface.Bus(bustype='socketcan', channel='can0')
            # msg = can.message.Message(arbitration_id=0x00FFAB80, bytearray([0, 0, 0, 0, 0, 0, 0, 0]))
            # for i in range(50):
            #   bus.send(msg)
            #   time.sleep(.0003)
            #
            #       which results in stuff like
            #
            # altendky@tp:/epc/bin$ can0; candump -L -x can0,#FFFFFFFF | grep -E '(0[04]FFAB(88|90|80)|can0 2)'
            # (1469135699.755374) can0 00FFAB80#0000000000000000
            # (1469135699.755462) can0 00FFAB80#0000000000000000
            # (1469135699.755535) can0 00FFAB80#0000000000000000
            # (1469135699.755798) can0 00FFAB80#0000000000000000
            # (1469135699.755958) can0 00FFAB80#0000000000000000
            # (1469135699.756132) can0 00FFAB80#0000000000000000
            # (1469135699.756446) can0 00FFAB80#0000000000000000
            # (1469135699.756589) can0 20000004#000C000000000000
            # (1469135699.756589) can0 20000004#0030000000000000
            # (1469135699.756731) can0 00FFAB80#0000000000000000
            # (1469135699.757004) can0 00FFAB80#0000000000000000
            # (1469135699.757187) can0 00FFAB80#0000000000000000
            # (1469135699.757308) can0 20000040#0000000000000000
            # (1469135699.757460) can0 00FFAB80#0000000000000000
            # (1469135699.757634) can0 00FFAB80#0000000000000000
            # (1469135699.757811) can0 00FFAB80#0000000000000000
            # (1469135699.757980) can0 00FFAB80#0000000000000000
            # (1469135699.758173) can0 00FFAB80#0000000000000000
            # (1469135699.758319) can0 00FFAB80#0000000000000000
            # (1469135699.758392) can0 00FFAB80#0000000000000000
            # (1469135699.758656) can0 00FFAB80#0000000000000000
            # (1469135699.758726) can0 00FFAB80#0000000000000000
            # (1469135699.758894) can0 00FFAB80#0000000000000000

            if isinstance(self.bus, can.BusABC):
                # TODO: this is a hack to allow detection of transmitted
                #       messages later
                msg.timestamp = None

                # TODO: I would use message=message (or msg=msg) but:
                #       https://bitbucket.org/hardbyte/python-can/issues/52/inconsistent-send-signatures
                self.bus.send(msg)

                # TODO: get a real value for sent, but for now python-can
                #       doesn't provide that info.  also, it would be async...
                sent = True

                time.sleep(0.0005)
                if sent and on_success is not None:
                    on_success()
            else:
                # TODO: I would use message=message (or msg=msg) but:
                #       https://bitbucket.org/hardbyte/python-can/issues/52/inconsistent-send-signatures
                sent = self.bus._send(msg, on_success=on_success, passive=passive)

            if self.auto_disconnect:
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

    def terminate(self):
        self.set_bus()
        logging.debug('{} terminated'.format(object.__repr__(self)))

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
            self.set_filters(self.filters)
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

        if isinstance(self.bus, can.BusABC):
            self.notifier.moveToThread(None)
        else:
            app = QApplication.instance()
            if app is not None:
                self.notifier.moveToThread(app.thread())

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

    def set_filters(self, filters):
        self.filters = filters
        real_bus = self.bus
        if real_bus is not None:
            if hasattr(real_bus, 'setFilters'):
                real_bus.setFilters(can_filters=filters)


class NotifierProxy(QtCanListener):
    def __init__(self, bus, listeners=[], filtered_ids=None, parent=None):
        QtCanListener.__init__(self, receiver=self.message_received, parent=parent)

        # TODO: consider a WeakSet, though this may presently
        #       be keeping objects alive
        self.listeners = set(listeners)
        if filtered_ids is None:
            self.filtered_ids = None
        else:
            self.filtered_ids = set(filtered_ids)

    def message_received(self, message):
        if (self.filtered_ids is None or
                message.arbitration_id in self.filtered_ids):
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
