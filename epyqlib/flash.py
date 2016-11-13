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

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication


logger = logging.getLogger(__name__)


class Flasher(QObject):
    progress_messages = pyqtSignal(int)
    completed = pyqtSignal()
    done = pyqtSignal()
    failed = pyqtSignal()

    def __init__(self, file, bus, progress=None, parent=None):
        super().__init__(parent)

        self.failed.connect(self.done)
        self.completed.connect(self.done)

        self.protocol = ccp.Handler()
        self.protocol.messages_sent.connect(self.update_progress)
        from twisted.internet import reactor
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.protocol,
            reactor=reactor,
            bus=bus)

        coff = epyqlib.ticoff.Coff()
        coff.from_stream(file)

        self.retries = 5

        self.sections = [s for s in coff.sections
                         if s.data is not None and s.virt_size > 0]

        download_messages_to_send = sum(
            [math.ceil(len(s.data) / 6) for s in self.sections])
        # For every 5 download messages there is also 1 set MTA and 1 CRC.
        # There will likely be a couple retries and there's a bit more overhead
        # to get started.
        self.total_messages_to_send = (
            download_messages_to_send * 7 / 5 + self.retries + 15)

        if progress is not None:
            self.connect_to_progress(progress=progress)

    def update_progress(self, messages_sent):
        self.progress_messages.emit(messages_sent)

    def connect_to_progress(self, progress):
        progress.setMinimum(0)
        progress.setMaximum(self.total_messages_to_send)
        self.progress_messages.connect(progress.setValue)

    def flash(self):
        # We should start sending before the bootloader is listening to help
        # make sure we catch it.
        d = ccp.retry(function=self.protocol.connect, times=self.retries,
                      acceptable=[ccp.RequestTimeoutError])
        # Since we will send multiple connects in most cases we should give
        # the bootloader a chance to respond to all of them before moving on.
        d.addCallback(lambda _: ccp.sleep(0.1 * self.retries))
        # unlock
        d.addCallback(
            lambda _: self.protocol.set_mta(
                address_extension=ccp.AddressExtension.configuration_registers,
                address=0)
        )
        d.addCallback(
            lambda _: self.protocol.unlock(section=ccp.Password.dsp_flash),
        )
        d.addCallback(
            lambda _: self.protocol.set_mta(
                address_extension=ccp.AddressExtension.flash_memory,
                address=0)
        )
        d.addCallbacks(
            lambda _: self.protocol.clear_memory()
        )

        self.protocol.continuous_crc = None

        for section in self.sections:
            if len(section.data) % 2 != 0:
                data = itertools.chain(section.data, [0])
            else:
                data = section.data
            callback = functools.partial(
                self.protocol.download_block,
                address_extension=ccp.AddressExtension.flash_memory,
                address=section.virt_addr,
                data=data
            )
            print('0x{:08X}'.format(section.virt_addr))
            d.addCallbacks(lambda _, cb=callback: cb())

        d.addCallback(lambda _: self.protocol.build_checksum(
            checksum=self.protocol.continuous_crc, length=0))
        d.addCallback(lambda _: self.protocol.disconnect())
        d.addCallback(lambda _: self.completed.emit())
        d.addErrback(lambda _: self.failed.emit())
        # d.addErrback(ccp.logit)

        logger.debug('---------- started')


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


def main(args=None):
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

    try:
        qt5reactor.install()
    except twisted.internet.error.ReactorAlreadyInstalledError:
        pass
    from twisted.internet import reactor

    real_bus = can.interface.Bus(bustype=args.interface,
                                 channel=args.channel,
                                 bitrate=args.bitrate)
    bus = epyqlib.busproxy.BusProxy(bus=real_bus, auto_disconnect=False)

    flasher = Flasher(file=args.file, bus=bus)

    flasher.flash()

    flasher.completed.connect(completed)
    flasher.failed.connect(failed)

    try:
        reactor.runReturn()
    except twisted.internet.error.ReactorAlreadyRunning:
        pass

    return app.exec()


def completed():
    print("Flashing completed successfully")
    QApplication.instance().quit()


def failed():
    print("Flashing failed")
    QApplication.instance().exit(1)


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
