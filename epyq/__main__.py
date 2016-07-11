#!/usr/bin/env python3

# TODO: get some docstrings in here!

import epyq.tee
import os
import sys

log = open(os.path.join(os.getcwd(), 'epyq.log'), 'w', encoding='utf-8')

if sys.stdout is None:
    sys.stdout = log
else:
    sys.stdout = epyq.tee.Tee([sys.stdout, log])

if sys.stderr is None:
    sys.stderr = log
else:
    sys.stderr = epyq.tee.Tee([sys.stderr, log])

try:
    import epyq.revision
except ImportError:
    pass
else:
    print(epyq.revision.hash)

import can
import canmatrix.importany as importany
import copy
import epyq.busproxy
import epyq.canneo
import epyq.device
import epyq.nv
from epyq.svgwidget import SvgWidget
import epyq.txrx
import functools
import io
import math
import platform

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                          QSettings, Qt, pyqtSlot, QMarginsF)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QLabel,
                             QListWidgetItem, QAction, QMenu)
from PyQt5.QtGui import QPixmap, QPicture
import time
import traceback

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def main(args=None):
    print('starting epyq')

    app = QApplication(sys.argv)
    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPyQ')

    interface = 'socketcan'
    channel = 'can0'

    # TODO: CAMPid 9756652312918432656896822
    if interface != 'offline':
        real_bus = can.interface.Bus(bustype=interface, channel=channel)
    else:
        real_bus = None
    bus = epyq.busproxy.BusProxy(bus=real_bus)

    ui = 'main.ui'
    # TODO: CAMPid 9549757292917394095482739548437597676742
    if not QFileInfo(ui).isAbsolute():
        ui_file = os.path.join(
            QFileInfo.absolutePath(QFileInfo(__file__)), ui)
    else:
        ui_file = ui
    ui_file = QFile(ui_file)
    ui_file.open(QFile.ReadOnly | QFile.Text)
    ts = QTextStream(ui_file)
    sio = io.StringIO(ts.readAll())
    ui = uic.loadUi(sio)

    ui.send_button.clicked.connect(
        functools.partial(
            bus.send,
            can.Message(extended_id=False,
                        arbitration_id=0x342,
                        dlc=1,
                        data=[0x42])
        )
    )

    matrix = list(importany.importany('AFE_CAN_ID247.sym').values())[0]
    neo = epyq.canneo.Neo(matrix=matrix,
                          frame_class=epyq.txrx.MessageNode,
                          signal_class=epyq.txrx.SignalNode)

    notifiees = [neo]

    notifier = bus.notifier
    for notifiee in notifiees:
        notifier.add(notifiee)

    device_file = 'example.epc'
    # TODO: CAMPid 9549757292917394095482739548437597676742
    if not QFileInfo(device_file).isAbsolute():
        device_file = os.path.join(
            os.getcwd(), device_file)
    else:
        device_file = device_file
    device = epyq.device.Device(file=device_file, bus=bus,
                                dash_only=True)
    ui.layout.addWidget(device.ui)

    ui.showFullScreen()

    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
