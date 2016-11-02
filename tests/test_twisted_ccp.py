import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
import can
import epyqlib.busproxy
import epyqlib.twisted.busproxy
import epyqlib.twisted.cancalibrationprotocol as ccp
import pytest
import qt5reactor
import time

from PyQt5.QtCore import QTimer


def test_main():
    qt5reactor.install()
    from twisted.internet import reactor
    real_bus = can.interface.Bus(bustype='socketcan', channel='can0')
    bus = epyqlib.busproxy.BusProxy(bus=real_bus)
    protocol = ccp.Handler()
    transport = epyqlib.twisted.busproxy.BusProxy(
        protocol=protocol,
        reactor=reactor,
        bus=bus)

    d = protocol.connect()
    d.addCallbacks(protocol.disconnect, logit)
    d.addBoth(logit)

    logging.debug('---------- started')
    QTimer.singleShot(3000, reactor.stop)
    reactor.run()


def logit(it):
    logging.debug('logit(): {}'.format(it))


def test_IdentifierTypeError():
    with pytest.raises(ccp.IdentifierTypeError):
        ccp.HostCommand(code=ccp.CommandCode.connect,
                        extended_id=False)


def test_PayloadLengthError():
    with pytest.raises(ccp.PayloadLengthError):
        hc = ccp.HostCommand(code=ccp.CommandCode.connect)
        hc.payload = [0] * 20


def test_MessageLengthError():
    with pytest.raises(ccp.MessageLengthError):
        ccp.HostCommand(code=ccp.CommandCode.connect,
                        dlc=5)
