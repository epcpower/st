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
import epyq.listmenuview
import epyq.nv
from epyq.svgwidget import SvgWidget
import epyq.txrx
import functools
import io
import math
import platform
import socket
# TODO: figure out why this is negative on embedded... :[
socket.CAN_EFF_FLAG = abs(socket.CAN_EFF_FLAG)

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                          QSettings, Qt, pyqtSlot, QMarginsF, QTextCodec)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QLabel,
                             QListWidgetItem, QAction, QMenu, QFrame,
                             QAbstractScrollArea)
from PyQt5.QtGui import QPixmap, QPicture
import time
import traceback

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def load_ui(filename):
    # TODO: CAMPid 9549757292917394095482739548437597676742
    if not QFileInfo(filename).isAbsolute():
        ui_file = os.path.join(
            QFileInfo.absolutePath(QFileInfo(__file__)), filename)
    else:
        ui_file = filename
    ui_file = QFile(ui_file)
    ui_file.open(QFile.ReadOnly | QFile.Text)
    ts = QTextStream(ui_file)
    sio = io.StringIO(ts.readAll())
    return uic.loadUi(sio)


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
    ''')

    QTextCodec.setCodecForLocale(QTextCodec.codecForName('UTF-8'))

    ui = load_ui('main.ui')

    bus = epyq.busproxy.BusProxy()

    device_file = 'example_hmi.epc'
    # TODO: CAMPid 9549757292917394095482739548437597676742
    if not QFileInfo(device_file).isAbsolute():
        device_file = os.path.join(
            os.getcwd(), device_file)
    else:
        device_file = device_file

    device = epyq.device.Device(file=device_file,
                                bus=bus,
                                tabs=[],
                                elements=[epyq.device.Elements.dash,
                                          epyq.device.Elements.nv],
                                rx_interval=1)
    # TODO: CAMPid 9757656124812312388543272342377

    interface = 'socketcan'
    channel = 'can0'

    # TODO: CAMPid 9756652312918432656896822
    if interface != 'offline':
        real_bus = can.interface.Bus(bustype=interface, channel=channel,
                                     can_filters=[])
    else:
        real_bus = None
    bus.set_bus(bus=real_bus)

    import json
    from collections import OrderedDict

    with open('menu.json') as f:
        menu = json.load(f, object_pairs_hook=OrderedDict)

    menu_root = epyq.listmenu.Node(text='Main Menu')

    def traverse(dict_node, model_node):
        for key, value in dict_node.items():
            child = epyq.listmenu.Node(text=key)
            model_node.append_child(child)
            if isinstance(value, OrderedDict):
                traverse(dict_node=value,
                         model_node=child)

    traverse(menu, menu_root)

    def focus_dash(name, dash):
        filters = [
            {
                'can_id': frame.id | socket.CAN_EFF_FLAG,
                'can_mask': socket.CAN_EFF_MASK |
                            socket.CAN_EFF_FLAG |
                            socket.CAN_RTR_FLAG
            }
            for frame in device.dash_connected_frames[name]
        ]
        real_bus.setFilters(filters)
        ui.stacked.setCurrentWidget(dash)

    dash_item = epyq.listmenu.Node(text='Dashboards')
    menu_root.append_child(dash_item)
    for name, dash in device.dash_uis.items():
        node = epyq.listmenu.Node(
            text=name,
            action=functools.partial(
                focus_dash,
                name=name,
                dash=dash
            )
        )
        dash_item.append_child(node)
        ui.stacked.addWidget(dash)

    nv_filters = [
        {
            'can_id': frame.id | socket.CAN_EFF_FLAG,
            'can_mask': socket.CAN_EFF_MASK |
                        socket.CAN_EFF_FLAG |
                        socket.CAN_RTR_FLAG
        }
        for frame in [device.nvs.set_frames[0], device.nvs.status_frames[0]]
        ]

    def focus_nv(name, nv):
        real_bus.setFilters(nv_filters)

        nv.read_from_device()
        # TODO: actually wait for a response
        print('{name}: {value}'.format(name=name,
                                       value=nv.value))
        ui.stacked.setCurrentWidget(nv.ui)

    nv_item = epyq.listmenu.Node(text='Parameters')
    menu_root.append_child(nv_item)
    for nv in device.nvs.children:
        nv.ui = load_ui('parameter_edit.ui')
        nv.ui.from_device.set_signal(nv.status_signal)
        nv.ui.to_device.set_signal(nv)
        nv.status_signal.value_changed.connect(nv.value_changed)
        # nv.status_signal.value_changed.connect(testy)
        ui.stacked.addWidget(nv.ui)
        node = epyq.listmenu.Node(
            text=nv.name,
            action=functools.partial(
                focus_nv,
                name=nv.name,
                nv=nv
            )
        )
        nv_item.append_child(node)

    menu_model = epyq.listmenu.ListMenuModel(root=menu_root)
    menu = epyq.listmenuview.ListMenuView()
    menu.setModel(menu_model)
    ui.stacked.addWidget(menu)

    def to_menu():
        real_bus.setFilters(can_filters=[])
        ui.stacked.setCurrentWidget(menu)

    ui.menu_button.clicked.connect(to_menu)

    ui.stacked.setCurrentWidget(menu)

    def traverse(widget):
        try:
            widget.setFlat(True)
        except AttributeError:
            pass

        if isinstance(widget, QAbstractScrollArea):
            widget.setFrameStyle(QFrame.NoFrame)

        for child in widget.children():
            traverse(child)

    traverse(ui)

    if os.environ.get('QT_QPA_PLATFORM', None) == 'linuxfb':
        ui.showFullScreen()
    else:
        ui.show()

    # TODO: CAMPid 98754713241621231778985432
    # ui.menu_button.setMaximumWidth(ui.menu_button.height())

    menu.update_calculated_layout()

    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
