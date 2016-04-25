#!/usr/bin/env python3.4

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

import can
import copy
import epyq.busproxy
import epyq.busselector
import epyq.canneo
import epyq.fileselector
import epyq.nv
import epyq.txrx
import epyq.widgets.progressbar
import epyq.widgets.lcd
import functools
import io
import math
import platform

from epyq.device import Device

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                          QSettings, Qt)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QLabel,
                             QListWidgetItem, QAction, QMenu)
from PyQt5.QtGui import QPixmap
import time
import traceback

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 9756562638416716254289247326327819
class Window(QtWidgets.QMainWindow):
    def __init__(self, ui_file, bus, devices=[], parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        self.bus = bus

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        self.setWindowIcon(ico)

        ui = ui_file
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
        self.ui = uic.loadUi(sio, self)

        self.ui.busselector.select_bus.connect(self.select_bus)
        load_device = functools.partial(self.load_device, file=None)
        self.ui.load_device_button.clicked.connect(load_device)

        self.ui.action_About.triggered.connect(self.about)

        for file in devices:
            self.load_device(file)
        self.ui.device_list.itemActivated.connect(self.device_activated)
        self.ui.device_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.device_list.customContextMenuRequested.connect(
            self.device_context_menu
        )

    def device_context_menu(self, position):
        item = self.ui.device_list.itemAt(position)

        if item is None:
            return

        menu = QMenu()
        remove_device_action = menu.addAction('Close')
        action = menu.exec_(self.ui.device_list.mapToGlobal(position))
        if action is remove_device_action:
            self.remove_device(item)

    def about(self):
        box = QMessageBox()
        box.setWindowTitle("About EPyQ")

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        box.setWindowIcon(ico)

        message = [
            __copyright__,
            __license__
        ]
        
        try:
            import epyq.revision
        except ImportError:
            pass
        else:
            message.append(epyq.revision.hash)

        box.setText('\n'.join(message))
        box.exec_()

    def add_device(self, device):
        self.ui.stacked.addWidget(device.ui)
        self.ui.stacked.setCurrentWidget(device.ui)
        item = QListWidgetItem(device.name)
        item.setData(QtCore.Qt.UserRole, device.ui)
        self.ui.device_list.addItem(item)

    def remove_device(self, item):
        device = item.data(QtCore.Qt.UserRole)

        self.ui.stacked.removeWidget(device)
        self.ui.device_list.takeItem(self.ui.device_list.currentRow())

    def select_bus(self, interface, channel, bitrate):
        self.bus.set_bus(None)
        # TODO: CAMPid 9756652312918432656896822
        if interface != 'offline':
            real_bus = can.interface.Bus(bustype=interface,
                                         channel=channel,
                                         bitrate=bitrate)
        else:
            real_bus = None
        self.bus.set_bus(bus=real_bus)

    def device_activated(self, item):
        device = item.data(QtCore.Qt.UserRole)
        self.ui.stacked.setCurrentWidget(device)

    def load_device(self, file=None):
        if file is None:
            filters = [
                ('EPC Packages', ['epc', 'epz']),
                ('All Files', ['*'])
            ]
            file = file_dialog(filters)

            if file is None:
                return

        device = Device(file=file, bus=self.bus)
        self.add_device(device)


def file_dialog(filters, default=0):
    # filters = [
    #     ('EPC Packages', ['epc', 'epz']),
    #     ('All Files', ['*'])
    # ]
    # TODO: CAMPid 97456612391231265743713479129

    filter_strings = ['{} ({})'.format(f[0],
                                       ' '.join(['*.'+e for e in f[1]])
                                       ) for f in filters]
    filter_string = ';;'.join(filter_strings)

    file = QFileDialog.getOpenFileName(
            filter=filter_string,
            initialFilter=filter_strings[default])[0]

    if len(file) == 0:
        file = None

    return file


# TODO: Consider updating from...
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/eric6.py#l134

# TODO: deal with licensing for swiped code (GPL3)
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/LICENSE.GPL3

def excepthook(excType, excValue, tracebackobj):
    """
    Global function to catch unhandled exceptions.

    @param excType exception type
    @param excValue exception value
    @param tracebackobj traceback object
    """
    separator = '-' * 70
    email = "kyle.altendorf@epcpower.com"
    notice = \
        """An unhandled exception occurred. Please report the problem via email to:\n"""\
        """\t\t%s\n\n"""\
        """A log has been written to "%s".\n\nError information:\n""" % \
        (email, log.name)
    # TODO: add something for version
    versionInfo=""
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

    tbinfofile = io.StringIO()
    traceback.print_tb(tracebackobj, None, tbinfofile)
    tbinfofile.seek(0)
    tbinfo = tbinfofile.read()
    errmsg = '%s: \n%s' % (str(excType), str(excValue))
    sections = [separator, timeString, separator, errmsg, separator, tbinfo]
    msg = '\n'.join(sections)

    errorbox = QMessageBox()
    errorbox.setWindowTitle("EPyQ FAIL!")
    errorbox.setIcon(QMessageBox.Critical)

    # TODO: CAMPid 980567566238416124867857834291346779
    ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
    ico = QtGui.QIcon(ico_file)
    errorbox.setWindowIcon(ico)

    complete = str(notice) + str(msg) + str(versionInfo)

    sys.stderr.write(complete)
    errorbox.setText(complete)
    errorbox.exec_()


# TODO: CAMPid 907616231629845659923471326
def select_bus():
    bs = epyq.busselector.Selector()
    bs.exec()
    return bs.selected()


# TODO: CAMPid 907616231629845659923471326
def select_recent_file(recent=[]):
    fs = epyq.fileselector.Selector(recent=recent)
    fs.exec()
    return fs.selected()


def main(args=None):
    print('starting epyq')

    app = QApplication(sys.argv)
    sys.excepthook = excepthook
    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPyQ')

    settings = QSettings(app.organizationName(),
                         app.applicationName())

    if args is None:
        import argparse

        ui_default = 'main.ui'

        parser = argparse.ArgumentParser()

        default_interfaces = {
            'Linux': 'socketcan',
            'Windows': 'pcan'
        }
        parser.add_argument('--interface',
                            default=default_interfaces[platform.system()])

        parser.add_argument('--channel', default=None)
        parser.add_argument('--ui', default=ui_default)
        parser.add_argument('--generate', '-g', action='store_true')
        parser.add_argument('devices', nargs='*')
        args = parser.parse_args()

        if args.channel is None:
            interface = 'offline'
            channel = ''
        else:
            interface = args.interface
            channel = args.channel

    # TODO: find the 'proper' way to handle both quoted and non-quoted paths
    for i, arg in enumerate(args.devices):
        if arg[0] == arg[-1] and len(arg) >= 2:
            if arg[0] in ['"', "'"]:
                args.devices[i] = arg[1:-1]

    # TODO: CAMPid 9756652312918432656896822
    if interface != 'offline':
        real_bus = can.interface.Bus(bustype=interface, channel=channel)
    else:
        real_bus = None
    bus = epyq.busproxy.BusProxy(bus=real_bus)

    if args.generate:
        print('generating')
        start_time = time.monotonic()

        frame_name = 'StatusControlVolts2'
        signal_name = 'n15V_Supply'
        frame = epyq.canneo.Frame(matrix_tx.frameByName(frame_name))
        signal = epyq.canneo.Signal(frame.frame.signalByName(signal_name), frame)

        message = can.Message(extended_id=frame.frame._extended,
                              arbitration_id=frame.frame._Id,
                              dlc=frame.frame._Size)

        messages = [
            can.Message(extended_id=True,
                        arbitration_id=486517239,
                        dlc=8,
                        data=bytearray([0, 1, 0, 160, 7, 208, 5, 220])),
            can.Message(extended_id=True,
                        arbitration_id=486517239,
                        dlc=8,
                        data=bytearray([0, 4, 0, 160, 1, 77, 0, 160])),
            can.Message(extended_id=True,
                        arbitration_id=218082369,
                        dlc=8,
                        data=bytearray([0, 0, 0, 3, 0, 0, 0, 42]))
        ]

        # Copy from PCAN generated and logged messages
        # Bus=2,ID=486517239x,Type=D,DLC=8,DA=0,Data=0 1 0 160 7 208 5 220 ,
        # Bus=2,ID=486517239x,Type=D,DLC=8,DA=0,Data=0 4 0 160 1 77 0 160 ,
        # Bus=2,ID=218082369x,Type=D,DLC=8,DA=0,Data=0 0 0 3 0 0 0 42 ,

        last_send = 0
        while True:
            time.sleep(0.010)
            now = time.monotonic()
            if now - last_send > 0.100:
                last_send = now
                elapsed_time = time.monotonic() - start_time
                value = math.sin(elapsed_time) / 2
                value *= 2
                nominal = -15
                value += nominal
                human_value = value
                value /= float(signal.signal._factor)
                value = round(value)
                print('{:.3f}: {}'.format(elapsed_time, value))
                message.data = frame.pack([value, 0, 1, 2])
                bus.send(message)

                bus.send(can.Message(extended_id=True,
                                     arbitration_id=0xFF9B41,
                                     dlc=8,
                                     data=bytearray([0, 0, 0, 0, 0, 0, 0,
                                         int(human_value > nominal)])))

                for m in messages:
                    bus.send(m)
        sys.exit(0)

    devices = [os.path.abspath(f) for f in args.devices]

    window = Window(ui_file=args.ui, devices=devices, bus=bus)

    window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
