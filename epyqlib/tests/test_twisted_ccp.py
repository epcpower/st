import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
import can
import epyqlib.busproxy
import epyqlib.twisted.busproxy
import epyqlib.twisted.cancalibrationprotocol as ccp
import pytest
import sys

from PyQt5.QtCore import QTimer

# import epyqlib.ticoff as ticoff
#
# files = [
#     '/epc/t/409/afe.out',
#     '/epc/t/409/ul1741.lc12_3.out',
#     '/epc/t/409/RS12_04c.out'
# ]
#
# files = {file: ticoff.Coff(file) for file in files}
#
# import itertools
#
#
# def endswap(l):
#     return itertools.chain(*((b, a) for a, b in zip(l[::2], l[1::2])))
#
#
# for file, c in sorted(files.items()):
#     print('\n\n\n----- {}'.format(file))
#     print('\n'.join([str((i,
#                           s.name,
#                           hex(s.virt_addr),
#                           s.virt_size,
#                           len(s.data),  # if s.data is not None else -1,
#                           'even' if len(s.data) % 2 else 'odd',
#                           ' '.join(list('{:02X}'.format(b) for b in
#                                         itertools.islice(endswap(s.data), 10))),
#                           # if s.data is not None else []
#                           ' '.join(list('{:02X}'.format(b) for b in
#                                         itertools.islice(endswap(s.data), max(0,
#                                                                               len(
#                                                                                   s.data) - 10),
#                                                          None))),
#                           # if s.data is not None else []
#                           s.data[:30]
#                           )) for i, s
#                      in enumerate(c.sections) if s.data is not None]))


@pytest.mark.require_device
def test_main():
    # TODO: CAMPid 03127876954165421679215396954697
    # https://github.com/kivy/kivy/issues/4182#issuecomment-253159955
    # fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
    if 'twisted.internet.reactor' in sys.modules:
        del sys.modules['twisted.internet.reactor']

    import qt5reactor
    qt5reactor.install()

    from twisted.internet import reactor
    real_bus = can.interface.Bus(bustype='socketcan', channel='can0')
    bus = epyqlib.busproxy.BusProxy(bus=real_bus)

    device = epyqlib.device.Device(
        file=epyqlib.tests.common.devices['customer'],
        node_id=247,
    )

    tx_signal = device.neo_frames.signal_by_path(
        'CCP', 'Connect', 'CommandCounter'
    )
    rx_signal = device.neo_frames.signal_by_path(
        'CCPResponse', 'Connect', 'CommandCounter'
    )
    protocol = ccp.Handler(
        endianness='little' if tx_signal.little_endian else 'big',
        tx_id=tx_signal.frame.id,
        rx_id=rx_signal.frame.id,
    )
    transport = epyqlib.twisted.busproxy.BusProxy(
        protocol=protocol,
        reactor=reactor,
        bus=bus,
    )

    d = protocol.connect()
    d.addCallback(lambda _: protocol.set_mta(
        address_extension=ccp.AddressExtension.flash_memory,
        address=0x310000,
    ))
    d.addCallback(lambda _: protocol.disconnect())
    d.addBoth(logit)

    logging.debug('---------- started')
    QTimer.singleShot(3000, reactor.stop)
    reactor.run()


def logit(it):
    logging.debug('logit(): ({}) {}'.format(type(it), it))


def test_identifier_type_error():
    with pytest.raises(ccp.IdentifierTypeError):
        ccp.HostCommand(code=ccp.CommandCode.connect,
                        extended_id=False)


def test_payload_assignment_error():
    with pytest.raises(AttributeError):
        hc = ccp.HostCommand(code=ccp.CommandCode.connect)
        hc.payload = 0


def test_message_length_error():
    with pytest.raises(ccp.MessageLengthError):
        ccp.HostCommand(code=ccp.CommandCode.connect,
                        dlc=5)
