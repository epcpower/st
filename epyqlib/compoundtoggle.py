#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CompoundToggle(QWidget):
    def __init__(self, parent=None, in_designer=False):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'compoundtoggle.ui')

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

        self.ui.command.in_designer = self.in_designer
        self.ui.status_on.in_designer = self.in_designer
        self.ui.status_off.in_designer = self.in_designer

        if self.in_designer:
            self.ui.status_off.set_value(self.ui.status_off.on_value)
            self.ui.status_on.set_value(self.ui.status_off.on_value)

    @pyqtProperty(str)
    def box_title(self):
        return self.ui.box.title()

    @box_title.setter
    def box_title(self, title):
        self.ui.box.setTitle(title)

    @pyqtProperty('QString')
    def command_signal_path(self):
        return self.ui.command.signal_path

    @command_signal_path.setter
    def command_signal_path(self, value):
        self.ui.command.signal_path = value

    @pyqtProperty('QString')
    def status_signal_path(self):
        return self.ui.status_off.signal_path

    @status_signal_path.setter
    def status_signal_path(self, value):
        self.ui.status_off.signal_path = value
        self.ui.status_on.signal_path = value

    @pyqtProperty(int)
    def on_value(self):
        return self.ui.status_on.on_value

    @on_value.setter
    def on_value(self, new_on_value):
        self.ui.status_on.on_value = new_on_value

    @pyqtProperty(bool)
    def status_on_automatic_off_color(self):
        return self.ui.status_on.automatic_off_color

    @status_on_automatic_off_color.setter
    def status_on_automatic_off_color(self, automatic):
        self.ui.status_on.automatic_off_color = automatic

    @pyqtProperty(QColor)
    def status_on_on_color(self):
        return self.ui.status_on.on_color

    @status_on_on_color.setter
    def status_on_on_color(self, new_color):
        self.ui.status_on.on_color = new_color

    @pyqtProperty(QColor)
    def status_on_manual_off_color(self):
        return self.ui.status_on.manual_off_color

    @status_on_manual_off_color.setter
    def status_on_manual_off_color(self, new_color):
        self.ui.status_on.manual_off_color = new_color

    @pyqtProperty(int)
    def off_value(self):
        return self.ui.status_off.on_value

    @off_value.setter
    def off_value(self, new_off_value):
        self.ui.status_off.on_value = new_off_value
        if self.in_designer:
            self.ui.status_off.set_value(new_off_value)
            self.ui.status_on.set_value(new_off_value)

    @pyqtProperty(bool)
    def status_off_automatic_off_color(self):
        return self.ui.status_off.automatic_off_color

    @status_off_automatic_off_color.setter
    def status_off_automatic_off_color(self, automatic):
        self.ui.status_off.automatic_off_color = automatic

    @pyqtProperty(QColor)
    def status_off_on_color(self):
        return self.ui.status_off.on_color

    @status_off_on_color.setter
    def status_off_on_color(self, new_color):
        self.ui.status_off.on_color = new_color

    @pyqtProperty(QColor)
    def status_off_manual_off_color(self):
        return self.ui.status_off.manual_off_color
    
    @status_off_manual_off_color.setter
    def status_off_manual_off_color(self, new_color):
        self.ui.status_off.manual_off_color = new_color


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
