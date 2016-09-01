#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import functools
import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class NumberPad(QWidget):
    def __init__(self, parent=None, in_designer=False, action=None):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'numberpad.ui')

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

        self.action = action
        self.ui.accept_button.clicked.connect(self.accept)
        self.ui.cancel_button.clicked.connect(
            functools.partial(self.exit, value=None))

        for number in range(10):
            button = getattr(self.ui, 'button_{}'.format(number))
            button.clicked.connect(
                functools.partial(
                    self.ui.edit.insert,
                    str(number)
                )
            )

        self.ui.button_decimal.clicked.connect(
            functools.partial(
                self.ui.edit.insert,
                '.'
            )
        )
        self.ui.button_backspace.clicked.connect(self.ui.edit.backspace)

    def focus(self, value, action, label=''):
        self.ui.label.setText(label)
        self.ui.edit.setText(str(value))
        self.action = action
        self.parent().setCurrentWidget(self)

    def accept(self):
        try:
            value = float(self.ui.edit.text())
        except ValueError:
            value = None

        self.exit(value=value)

    def exit(self, value):
        self.action(value=value)

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
