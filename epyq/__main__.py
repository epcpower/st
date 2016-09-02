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
import epyq.hmidialog
import epyq.listmenuview
import epyq.numberpad
import epyq.nv
import epyq.parameteredit
from epyq.svgwidget import SvgWidget
import epyq.txrx
import epyq.wehmd
import functools
import io
import math
import platform
import socket
import subprocess
import textwrap
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

        QAbstractScrollArea {
            qproperty-frameShape: NoFrame;
        }

        QPushButton {
            qproperty-flat: true;
            width: 40px;
            height: 40px;
        }

        QFrame {
            qproperty-frameShadow: Plain;
        }

        QLineEdit, QPushButton {
            border-radius: 10px;
        }

        QLineEdit {
            border: 4px solid #2270A5;
        }

        QPushButton {
            border: 4px solid #21A558;
        }

        QLineEdit {
            qproperty-frame: false;
        }

        QLineEdit[enabled=false] {
            border: 4px solid gray;
        }

        QLineEdit[enabled=true] {
            qproperty-clearButtonEnabled: true;
            padding: 0 8px;
            selection-background-color: darkgray;
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

    nv_filters = [
        {
            'can_id': device.nvs.status_frames[0].id | socket.CAN_EFF_FLAG,
            'can_mask': socket.CAN_EFF_MASK |
                        socket.CAN_EFF_FLAG |
                        socket.CAN_RTR_FLAG
        }
    ]

    number_pad = epyq.numberpad.NumberPad()
    ui.stacked.addWidget(number_pad)

    node = epyq.listmenu.Node(
        text='Number Pad',
        action=functools.partial(
            number_pad.focus,
            value=17,
            action=lambda value: to_menu()
        )
    )
    menu_root.append_child(node)

    def focus_nv(widget):
        real_bus.setFilters(nv_filters)

        widget.nv.read_from_device()
        ui.stacked.setCurrentWidget(widget)

    nv_item = epyq.listmenu.Node(text='Parameters')
    menu_root.append_child(nv_item)
    for nv in device.nvs.children:
        widget = epyq.parameteredit.ParameterEdit(edit=number_pad, nv=nv)

        ui.stacked.addWidget(widget)
        node = epyq.listmenu.Node(
            text=nv.name,
            action=functools.partial(
                focus_nv,
                widget=widget
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

    def service_restart():
        hmd = epyq.wehmd.Wehmd()
        hmd.write_boot_mode(1)
        subprocess.run('reboot')

    hmi_dialog = epyq.hmidialog.HmiDialog()

    display_service_node = epyq.listmenu.Node(text='Display Service')
    menu_root.append_child(display_service_node)

    node = epyq.listmenu.Node(
        text='Service Reboot',
        action=functools.partial(
            hmi_dialog.focus,
            ok_action=service_restart,
            cancel_action=to_menu,
            label=textwrap.dedent('''\
                Reboot into maintenance mode?

                Insert configured USB stick first.''')
        )
    )

    display_service_node.append_child(node)
    ui.stacked.addWidget(hmi_dialog)

    def calibrate_touchscreen():
        os.remove('/opt/etc/pointercal')
        subprocess.run('reboot')

    node = epyq.listmenu.Node(
        text='Calibrate Touchscreen',
        action=functools.partial(
            hmi_dialog.focus,
            ok_action=calibrate_touchscreen,
            cancel_action=to_menu,
            label=textwrap.dedent('''\
                Reboot and calibrate touchscreen?''')
        )
    )

    display_service_node.append_child(node)

    def traverse(dict_node, menu_node):
        for key, value in dict_node.items():
            if isinstance(value, dict):
                action = None
            else:
                ui.stacked.addWidget(value)

                action = functools.partial(
                    focus_dash,
                    name=key,
                    dash=value
                )

            node = epyq.listmenu.Node(text=key, action=action)
            menu_node.append_child(node)
            if action is None:
                traverse(dict_node=value, menu_node=node)

    traverse(dict_node=device.dash_uis, menu_node=menu_root)

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
