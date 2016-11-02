# See file COPYING in this source tree
__copyright__ = ('\n'.join([
    'Copyright (c) Twisted Matrix Laboratories',
    # https://github.com/twisted/twisted/blob/4368c0b84b82f0791f6df52dc80328f7bd493547/src/twisted/internet/_posixserialport.py

    'Copyright 2016, EPC Power Corp.'
]))
__license__ = 'GPLv2+'


import epyqlib.canneo


class BusProxy(epyqlib.canneo.QtCanListener):
    def __init__(self, protocol, reactor, bus, parent=None):
        epyqlib.canneo.QtCanListener.__init__(self,
                                              receiver=self.readEvent,
                                              parent=parent)

        self._bus = bus
        self._reactor = reactor
        self._protocol = protocol

        self._bus.notifier.add(self)
        self._protocol.makeConnection(self)
        # self.startReading()

    def write(self, message):
        return self._bus.send(msg=message)


    def readEvent(self, message):
        """
        Some data's readable from serial device.
        """
        return self._protocol.dataReceived(message)


    def connectionLost(self, reason):
        """
        Called when the serial port disconnects.
        Will call C{connectionLost} on the protocol that is handling the
        serial data.
        """
        abstract.FileDescriptor.connectionLost(self, reason)
        self._serial.close()
        self.protocol.connectionLost(reason)
