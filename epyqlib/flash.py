import logging
import argparse
import can
import epyqlib.busproxy
import epyqlib.canneo
import epyqlib.ticoff
import epyqlib.twisted.busproxy
import epyqlib.twisted.cancalibrationprotocol as ccp
import functools
import itertools
import math
import platform
import qt5reactor
import signal
import sys
import twisted

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication


logger = logging.getLogger(__name__)


def parse_args(args):
    default = {
        'Linux': {'bustype': 'socketcan', 'channel': 'can0'},
        'Windows': {'bustype': 'pcan', 'channel': 'PCAN_USBBUS1'}
    }[platform.system()]

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--file', '-f', type=argparse.FileType('rb'), required=True)
    parser.add_argument('--interface', '-i', default=default['bustype'])
    parser.add_argument('--channel', '-c', default=default['channel'])
    parser.add_argument('--bitrate', '-b', default=250000)

    return parser.parse_args(args)


def main(args=None, create_app=True, create_reactor=True, progress=None):
    if create_app:
        app = QApplication(sys.argv)

    if args is None:
        args = sys.argv[1:]

    args = parse_args(args=args)

    if args.verbose >= 1:
        logger.setLevel(logging.DEBUG)

    if args.verbose >= 2:
        twisted.internet.defer.setDebugging(True)

    if args.verbose >= 3:
        logging.getLogger().setLevel(logging.DEBUG)

    if create_reactor:
        try:
            qt5reactor.install()
        except twisted.internet.error.ReactorAlreadyInstalledError:
            pass
    from twisted.internet import reactor

    real_bus = can.interface.Bus(bustype=args.interface,
                                 channel=args.channel,
                                 bitrate=args.bitrate)
    bus = epyqlib.busproxy.BusProxy(bus=real_bus, auto_disconnect=False)
    protocol = ccp.Handler()
    transport = epyqlib.twisted.busproxy.BusProxy(
        protocol=protocol,
        reactor=reactor,
        bus=bus)

    coff = epyqlib.ticoff.Coff()
    coff.from_stream(args.file)

    retries = 5

    sections = [s for s in coff.sections
                if s.data is not None and s.virt_size > 0]

    download_messages_to_send = sum(
        [math.ceil(len(s.data) / 6) for s in sections])
    # For every 5 download messages there is also 1 set MTA and 1 CRC.
    # There will likely be a couple retries and there's a bit more overhead
    # to get started.
    total_messages_to_send = download_messages_to_send * 7/5 + retries + 15

    if progress is not None:
        progress.setMinimum(0)
        progress.setMaximum(total_messages_to_send)
        protocol.messages_sent.connect(progress.setValue)

    # We should start sending before the bootloader is listening to help
    # make sure we catch it.
    d = ccp.retry(function=protocol.connect, times=retries,
              acceptable=[ccp.RequestTimeoutError])
    # Since we will send multiple connects in most cases we should give
    # the bootloader a chance to respond to all of them before moving on.
    d.addCallbacks(lambda _: ccp.sleep(0.1 * retries),
                   ccp.logit)
    # unlock
    d.addCallbacks(
        lambda _: protocol.set_mta(
            address_extension=ccp.AddressExtension.configuration_registers,
            address=0),
        ccp.logit
    )
    d.addCallbacks(
        lambda _: protocol.unlock(section=ccp.Password.dsp_flash),
        ccp.logit
    )
    d.addCallbacks(
        lambda _: protocol.set_mta(
            address_extension=ccp.AddressExtension.flash_memory,
            address=0),
        ccp.logit
    )
    d.addCallbacks(
        lambda _: protocol.clear_memory()
    )

    protocol.continuous_crc = None

    for section in sections:
        if len(section.data) % 2 != 0:
            data = itertools.chain(section.data, [0])
        else:
            data = section.data
        callback = functools.partial(
            protocol.download_block,
            address_extension=ccp.AddressExtension.flash_memory,
            address=section.virt_addr,
            data=data
        )
        print('0x{:08X}'.format(section.virt_addr))
        d.addCallbacks(lambda _, cb=callback: cb(), ccp.logit)

    d.addCallback(lambda _: protocol.build_checksum(
        checksum=protocol.continuous_crc, length=0))
    d.addCallbacks(lambda _: protocol.disconnect(), ccp.logit)
    d.addBoth(lambda result: done(result,
                                  create_app=create_app,
                                  create_reactor=create_reactor,
                                  bus=bus,
                                  progress=progress))
    d.addErrback(ccp.logit)

    logger.debug('---------- started')
    if create_reactor:
        try:
            reactor.runReturn()
        except twisted.internet.error.ReactorAlreadyRunning:
            pass

    if create_app:
        return app.exec()


def done(result, create_app, create_reactor, bus, progress):
    ccp.logit(result)

    bus.set_bus()

    if progress is not None:
        progress.close()

    if create_reactor:
        from twisted.internet import reactor
        reactor.stop()

    if create_app:
        QApplication.instance().quit()


def _entry_point():
    import traceback

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    def excepthook(excType, excValue, tracebackobj):
        logger.debug('Uncaught exception hooked:')
        traceback.print_exception(excType, excValue, tracebackobj)

    sys.excepthook = excepthook
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return main()


if __name__ == '__main__':
    sys.exit(_entry_point())
