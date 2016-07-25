#!/usr/bin/env python3

# TODO: get some docstrings in here!

# TODO: CAMPid 98852142341263132467998754961432
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

    app.setStyleSheet('''
        QWidget {
            font-size: 30px;
            font-family: Bitstream Vera Sans;
        }
        QListView::item
        {
            padding: 10px;
        }
    ''')

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

    bus = epyq.busproxy.BusProxy()

    device_file = 'example.epc'
    # TODO: CAMPid 9549757292917394095482739548437597676742
    if not QFileInfo(device_file).isAbsolute():
        device_file = os.path.join(
            os.getcwd(), device_file)
    else:
        device_file = device_file
    device = epyq.device.Device(file=device_file,
                                bus=bus,
                                dash_only=True,
                                rx_interval=1)
    # TODO: CAMPid 9757656124812312388543272342377

    CAN_EFF_MASK = 0x1FFFFFFF
    CAN_EFF_FLAG = 0x80000000
    CAN_RTR_FLAG = 0x40000000
    filters = [
        {
            'can_id': frame.id | CAN_EFF_FLAG,
            'can_mask': CAN_EFF_MASK | CAN_EFF_FLAG | CAN_RTR_FLAG
        }
        for frame in device.connected_frames
    ]

    interface = 'socketcan'
    channel = 'can0'

    # TODO: CAMPid 9756652312918432656896822
    if interface != 'offline':
        real_bus = can.interface.Bus(bustype=interface, channel=channel,
                                     can_filters=filters)
    else:
        real_bus = None
    bus.set_bus(bus=real_bus)

    import json
    from collections import OrderedDict

    with open('menu.json') as f:
        menu = json.load(f, object_pairs_hook=OrderedDict)

    menu_root = epyq.listmenu.Node(text='root')

    def traverse(dict_node, model_node):
        for key, value in dict_node.items():
            child = epyq.listmenu.Node(text=key)
            model_node.append_child(child)
            if isinstance(value, OrderedDict):
                traverse(dict_node=value,
                         model_node=child)

    traverse(menu, menu_root)

    menu_model = epyq.listmenu.ListMenuModel(root=menu_root)
    ui.list_menu_view.setModel(menu_model)

    ui.showFullScreen()

    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
