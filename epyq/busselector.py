#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import can
import functools
import io
import os
from PyQt5 import QtCore, QtWidgets, QtGui, uic, Qt
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                            pyqtSlot, QTimer)
from PyQt5.QtWidgets import QApplication, QMessageBox, QListWidgetItem
from PyQt5.QtGui import QPixmap
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'

def available():
    valid = []

    for interface in can.interface.VALID_INTERFACES:
        if interface == 'pcan':
            for n in range(1, 9):
                channel = 'PCAN_USBBUS{}'.format(n)
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append((interface, channel))
        elif interface == 'socketcan':
            for n in range(9):
                channel = 'can{}'.format(n)
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append((interface, channel))
            for n in range(9):
                channel = 'vcan{}'.format(n)
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append((interface, channel))
        else:
            print('Availability check not implemented for {}'
                  .format(interface), file=sys.stderr)

    return valid


# TODO: CAMPid 9756562638416716254289247326327819
class Selector(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent=parent)
        self.setWindowFlags(QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        self.setWindowIcon(ico)

        ui = 'busselector.ui'
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

        self.setWindowTitle('Bus Selector')

        self.separator = ' - '

        buses = available()

        notes = 'Available buses will be shown below.'

        if 'pcan' in [interface for interface, channel in buses]:
            notes += "\n'pcan' buses will flash the hardware LED when selected."

        self.ui.notes.setText(notes)

        for interface, channel in buses:
            self.ui.list.addItem('{}{}{}'.format(interface, self.separator,
                                                 channel))

        self.ui.list.itemSelectionChanged.connect(self.changed)
        self.ui.connect.setDisabled(True)

        self.ui.list.itemDoubleClicked.connect(self.double_clicked)
        self.ui.connect.clicked.connect(self.accept)
        self.ui.abort.clicked.connect(self.reject)

        self.selected_string = None

        self.flashing_buses = set()

    @pyqtSlot()
    def reject(self):
        self.stop_flashing()
        self.selected_string = None

        QtWidgets.QDialog.reject(self)

    @pyqtSlot()
    def accept(self):
        self.stop_flashing()
        QtWidgets.QDialog.accept(self)

    def stop_flashing(self):
        for bus in set(self.flashing_buses):
            self.flash(bus, False)

    @pyqtSlot(QListWidgetItem)
    def double_clicked(self, item):
        self.accept()

    def changed(self):
        if len(self.ui.list.selectedItems()) == 1:
            self.selected_string = self.ui.list.currentItem().text()

            interface, channel = self.selected()

            if interface == 'pcan':
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    self.flash(bus, True)
                    stop_flashing = functools.partial(self.flash, bus, False)
                    QTimer.singleShot(3000, stop_flashing)
        else:
            self.selected_string = None

        self.ui.connect.setDisabled(self.selected_string is None)

    def flash(self, bus, flash):
        flash = bool(flash)

        if flash:
            if bus in self.flashing_buses:
                return
            self.flashing_buses.add(bus)

        bus.flash(flash)

        if not flash:
            if bus not in self.flashing_buses:
                return
            bus.shutdown()
            self.flashing_buses.remove(bus)

    def selected(self):
        if self.selected_string is None:
            return None

        return self.selected_string.split(self.separator)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
