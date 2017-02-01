import textwrap

import attr
import twisted.internet.defer

from PyQt5 import QtCore, QtWidgets

import epyqlib.twisted.busproxy
import epyqlib.twisted.cancalibrationprotocol as ccp
import epyqlib.twisted.nvs
import epyqlib.utils.qt

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class UnsupportedError(Exception):
    pass


@attr.s
class DataLogger:
    nvs = attr.ib()
    bus = attr.ib()
    device = attr.ib()
    progress = attr.ib(default=attr.Factory(epyqlib.utils.qt.Progress))
    ccp_protocol = attr.ib(init=False)
    tx_id = attr.ib(default=0x1FFFFFFF)
    rx_id = attr.ib(default=0x1FFFFFF7)

    def __attrs_post_init__(self):
        self.ccp_protocol = ccp.Handler(tx_id=self.tx_id, rx_id=self.rx_id)
        from twisted.internet import reactor
        self.ccp_transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.ccp_protocol,
            reactor=reactor,
            bus=self.bus)
    
        self.nv_protocol = epyqlib.twisted.nvs.Protocol()
        self.nv_transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.nv_protocol,
            reactor=reactor,
            bus=self.bus)

    def pull_raw_log(self, path):
        d = self._pull_raw_log()
        d.addCallback(write_to_file, path=path)

        d.addErrback(epyqlib.utils.twisted.detour_result,
                     self.progress.fail)
        d.addErrback(epyqlib.utils.twisted.errbackhook)

        return d

    @twisted.internet.defer.inlineCallbacks
    def _pull_raw_log(self):
        try:
            signal = self.nvs.signal_from_names(
                'LoggerStatus01', 'ReadableOctets')
        except epyqlib.nv.NotFoundError as e:
            raise UnsupportedError(
                'Pull of raw log is not supported for this device') from e

        readable_octets = yield self.nv_protocol.read(signal)
        readable_octets = int(readable_octets)

        self.progress.configure(maximum=readable_octets)

        # TODO: hardcoded station address, tsk-tsk
        yield self.ccp_protocol.connect(station_address=0)
        data = yield self.ccp_protocol.upload_block(
            address_extension=ccp.AddressExtension.data_logger,
            address=0,
            octets=readable_octets,
            progress=self.progress
        )
        yield self.ccp_protocol.disconnect()

        seconds = self.progress.elapsed()

        completed_format = textwrap.dedent('''\
        Log successfully pulled

        Data time: {seconds:.3f} seconds for {bytes} bytes or {bps:.0f} bytes/second''')
        message = completed_format.format(
            seconds=seconds,
            bytes=readable_octets,
            bps=readable_octets / seconds
        )

        self.progress.complete(message=message)

        twisted.internet.defer.returnValue(data)


def write_to_file(data, path):
    with open(path, 'wb') as f:
        f.write(data)


def pull_raw_log(device, bus=None):
    if bus is None:
        bus = device.bus

    filters = [
        ('Raw', ['raw']),
        ('All Files', ['*'])
    ]
    filename = epyqlib.utils.qt.file_dialog(filters, save=True)

    # TODO: perhaps an exception for cancelation?  let caller ignore it?
    if filename is None:
        d = twisted.internet.defer.Deferred()
        d.callback(None)
        return d

    # TODO: CAMPid 9632763567954321696542754261546
    progress = QtWidgets.QProgressDialog(device.ui)
    flags = progress.windowFlags()
    flags &= ~QtCore.Qt.WindowContextHelpButtonHint
    progress.setWindowFlags(flags)
    progress.setWindowModality(QtCore.Qt.WindowModal)
    progress.setAutoReset(False)
    progress.setCancelButton(None)

    logger = epyqlib.datalogger.DataLogger(
        nvs=device.nvs,
        bus=bus,
        device=device)

    logger.progress.connect(
        progress=progress,
        label_text=('Pulling log...\n\n'
                    + logger.progress.default_progress_label)
    )
    return logger.pull_raw_log(path=filename)
