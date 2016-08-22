#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtWidgets import QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CompoundScale(QWidget):
    def __init__(self, parent=None, in_designer=False):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'compoundscale.ui')

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

        self.ui.command.in_designer = in_designer
        self.ui.echo.in_designer = in_designer
        self.ui.status.in_designer = in_designer

    @pyqtProperty(str)
    def command_frame(self):
        return self.ui.command.frame

    @command_frame.setter
    def command_frame(self, frame):
        self.ui.command.frame = frame

    @pyqtProperty(str)
    def command_signal(self):
        return self.ui.command.signal

    @command_signal.setter
    def command_signal(self, signal):
        self.ui.command.signal = signal

    @pyqtProperty(str)
    def echo_frame(self):
        return self.ui.echo.frame

    @echo_frame.setter
    def echo_frame(self, frame):
        self.ui.echo.frame = frame

    @pyqtProperty(str)
    def echo_signal(self):
        return self.ui.echo.signal

    @echo_signal.setter
    def echo_signal(self, signal):
        self.ui.echo.signal = signal

    @pyqtProperty(str)
    def status_frame(self):
        return self.ui.status.frame

    @status_frame.setter
    def status_frame(self, frame):
        self.ui.status.frame = frame

    @pyqtProperty(str)
    def status_signal(self):
        return self.ui.status.signal

    @status_signal.setter
    def status_signal(self, signal):
        self.ui.status.signal = signal

    @pyqtProperty(bool)
    def status_override_range(self):
        return self.ui.status.override_range

    @status_override_range.setter
    def status_override_range(self, override):
        self.ui.status.override_range = override

    @pyqtProperty(float)
    def status_minimum(self):
        return self.ui.status.minimum

    @status_minimum.setter
    def status_minimum(self, min):
        self.ui.status.minimum = float(min)

    @pyqtProperty(float)
    def status_maximum(self):
        return self.ui.status.maximum

    @status_maximum.setter
    def status_maximum(self, max):
        self.ui.status.maximum = float(max)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
