#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import functools
import io
import os
import time

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ParameterEdit(QWidget):
    def __init__(self, parent=None, in_designer=False, edit=None, nv=None):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'parameteredit.ui')

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

        self._edit = edit
        self.nv = nv

        self.ui.from_device.set_signal(self.nv.status_signal)
        self.ui.to_device.set_signal(self.nv)
        self.nv.status_signal.value_changed.connect(self.nv.value_changed)

        self.ui.edit_button.clicked.connect(self.edit)

    def edit(self):
        value = self.nv.get_human_value()
        self._edit.focus(value=value,
                         action=self.set_value,
                         label=self.nv.name)

    def set_value(self, value):
        if value is not None:
            for nv in self.nv.frame.signals:
                nv.read_from_device()
            time.sleep(0.05)
            self.nv.set_human_value(value)
            self.nv.write_to_device()

        self.parent().setCurrentWidget(self)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
