import logging
import argparse
import can
import epyqlib.busproxy
import epyqlib.canneo
import epyqlib.ticoff
import epyqlib.twisted.busproxy
import epyqlib.twisted.cancalibrationprotocol as ccp
import epyqlib.utils.twisted
import functools
import itertools
import math
import platform
import qt5reactor
import signal
import sys
import time
import twisted

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication


logger = logging.getLogger(__name__)


class Flasher(QObject):
    # TODO: CAMPid 7531968542136967546542452
    progress_messages = pyqtSignal(int)
    completed = pyqtSignal()
    done = pyqtSignal()
    failed = pyqtSignal()
    canceled = pyqtSignal()

    def __init__(self, file, bus, progress=None, retries=5, parent=None):
        super().__init__(parent)

        self.progress = progress
        self.deferred = None
        self._canceled = False

        self.completed.connect(self.done)

        self.protocol = ccp.Handler(endianness='big')
        self.protocol.messages_sent.connect(self.update_progress)
        from twisted.internet import reactor
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.protocol,
            reactor=reactor,
            bus=bus)

        coff = epyqlib.ticoff.Coff()
        coff.from_stream(file)

        self.retries = retries

        self.sections = [s for s in coff.sections
                         if s.data is not None and s.virt_size > 0]

        self.download_bytes = sum([len(s.data) for s in self.sections])
        download_messages_to_send = sum(
            [math.ceil(len(s.data) / 6) for s in self.sections])
        # For every 5 download messages there is also 1 set MTA and 1 CRC.
        # There will likely be a couple retries and there's a bit more overhead
        # to get started.
        self.total_messages_to_send = download_messages_to_send * 7 / 5 + 15

        self.connect_to_progress()

        self._data_start_time = None
        self.data_delta_time = None

    def update_progress(self, messages_sent):
        self.progress_messages.emit(messages_sent)

    def connect_to_progress(self, progress=None):
        if progress is not None:
            self.progress = progress

        if self.progress is not None:
            self.progress.setMinimumDuration(0)
            # Default to a busy indicator, progress maximum will be set later
            self.progress.setMinimum(0)
            self.progress.setMaximum(0)
            self.progress_messages.connect(self.progress.setValue)
            self.progress.canceled.connect(self.cancel)

    def disconnect_from_progress(self):
        if self.progress is not None:
            self.progress_messages.disconnect(self.progress.setValue)
            self.progress.canceled.disconnect(self.cancel)

            self.progress = None

    def set_progress_label(self, text):
        if self.progress is not None:
            self.progress.setLabelText(text)

    def set_progress_range(self):
        if self.progress is not None:
            self.progress.setMinimum(0)
            self.progress.setMaximum(self.total_messages_to_send)

    def show_progress(self):
        if self.progress is not None:
            self.progress.show()

    def hide_progress_cancel_button(self):
        if self.progress is not None:
            self.progress.setCancelButton(None)

    def cancel(self):
        if self.deferred is not None and not self._canceled:
            self._canceled = True
            self.disconnect_from_progress()
            self.protocol.cancel()
            self.deferred.cancel()

    def flash(self):
        # We should start sending before the bootloader is listening to help
        # make sure we catch it.

        self.set_progress_label('Searching...')
        self.show_progress()

        # let any buffered/old messages get dumped
        d = epyqlib.utils.twisted.sleep(0.5)
        self.deferred = d
        d.addCallback(lambda _: epyqlib.utils.twisted.retry(
            function=lambda: self.protocol.connect(timeout=0.2),
            times=self.retries,
            acceptable=[epyqlib.utils.twisted.RequestTimeoutError])
        )

        d.addCallback(lambda _: self.set_progress_label('Clearing...'))

        # Since we will send multiple connects in most cases we should give
        # the bootloader a chance to respond to all of them before moving on.
        d.addCallback(
            lambda _: epyqlib.utils.twisted.sleep(min(1, 0.01 * self.retries))
        )
        # unlock

        d.addCallback(lambda _: epyqlib.utils.twisted.timeout_retry(
            lambda : self.protocol.set_mta(
                address_extension=ccp.AddressExtension.configuration_registers,
                address=0)
        ))
        d.addCallback(lambda _: epyqlib.utils.twisted.timeout_retry(
            lambda : self.protocol.unlock(section=ccp.Password.dsp_flash)
        ))
        d.addCallback(lambda _: epyqlib.utils.twisted.timeout_retry(
            lambda : self.protocol.set_mta(
                address_extension=ccp.AddressExtension.flash_memory,
                address=0)
        ))
        d.addCallbacks(lambda _: epyqlib.utils.twisted.timeout_retry(
            self.protocol.clear_memory,
            times=2
        ))

        d.addCallback(lambda _: self.set_progress_label('Flashing...'))
        d.addCallback(lambda _: self.set_progress_range())
        d.addCallback(lambda _: self.hide_progress_cancel_button())

        d.addCallback(lambda _: self._start_timing_data())

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
            logger.debug('0x{:08X}'.format(section.virt_addr))
            d.addCallback(lambda _, cb=callback: cb())

        d.addCallback(lambda _: epyqlib.utils.twisted.sleep(1))
        d.addCallback(lambda _: self.protocol.build_checksum(
            checksum=self.protocol.continuous_crc, length=0))
        d.addCallback(lambda _: epyqlib.utils.twisted.sleep(1))
        d.addCallback(lambda _: self.protocol.disconnect())
        d.addCallback(lambda _: self._completed())
        d.addErrback(self._failed)

        logger.debug('---------- started')

    def _start_timing_data(self):
        self._data_start_time = time.monotonic()
        logger.debug('Started timing data at {}'.format(self._data_start_time))
        # return twisted.internet.defer.succeed()

    def _completed(self):
        self.data_delta_time = time.monotonic() - self._data_start_time
        self.completed.emit()

    def _failed(self, result):
        epyqlib.utils.twisted.logit(result)
        if self._canceled:
            self.canceled.emit()
        else:
            self.failed.emit()
        self.done.emit()


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

    qt5reactor.install()
    from twisted.internet import reactor

    reactor.runReturn()

    QApplication.instance().aboutToQuit.connect(about_to_quit)

    real_bus = can.interface.Bus(bustype=args.interface,
                                 channel=args.channel,
                                 bitrate=args.bitrate)
    bus = epyqlib.busproxy.BusProxy(bus=real_bus, auto_disconnect=False)

    flasher = Flasher(file=args.file, bus=bus)

    flasher.completed.connect(lambda f=flasher: completed(flasher=f))
    flasher.failed.connect(failed)
    flasher.done.connect(bus.set_bus)

    flasher.flash()

    return app.exec()


def about_to_quit():
    from twisted.internet import reactor
    reactor.stop()


def completed(flasher):
    print("Flashing completed successfully")
    print('Data time: {:.3f} seconds for {} bytes or {:.0f} bytes/second'
          .format(flasher.data_delta_time,
                  flasher.download_bytes,
                  flasher.download_bytes / flasher.data_delta_time))
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
