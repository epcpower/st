import logging
import sys

import PyQt5.QtCore
import PyQt5.QtWidgets

import epyqlib.busproxy
import epyqlib.device
import epyqlib.tests.common
import epyqlib.twisted.busproxy

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def run():
    app = PyQt5.QtWidgets.QApplication(sys.argv)

    # TODO: CAMPid 03127876954165421679215396954697
    # https://github.com/kivy/kivy/issues/4182#issuecomment-253159955
    # fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
    if 'twisted.internet.reactor' in sys.modules:
        del sys.modules['twisted.internet.reactor']

    import qt5reactor
    qt5reactor.install()

    from twisted.internet import reactor

    device = epyqlib.device.Device(
        file=epyqlib.tests.common.devices['customer'],
        node_id=247,
        # bus=bus,
    )
    device.ui.show()

    PyQt5.QtCore.QTimer.singleShot(1 * 1000, reactor.stop)
    reactor.run()

    return 0
