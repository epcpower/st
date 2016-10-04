#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import functools
import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class HmiDialog(QWidget):
    def __init__(self, parent=None, in_designer=False):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'hmidialog.ui')

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

        self.ok_action = None
        self.cancel_action = None
        self.ui.ok_button.clicked.connect(self.ok)
        self.ui.cancel_button.clicked.connect(self.cancel)

        self.label.setWordWrap(True)

    def focus(self, label, ok_action=None, cancel_action=None,
              enable_delay=1500):
        self.ok_action = ok_action
        self.ui.ok_button.setVisible(ok_action is not None)
        self.cancel_action = cancel_action
        self.ui.cancel_button.setVisible(cancel_action is not None)

        self.ui.label.setText(label)

        if enable_delay > 0:
            self.enable_buttons(False)
        else:
            self.enable_buttons(True)

        self.parent().setCurrentWidget(self)

        if enable_delay > 0:
            QTimer.singleShot(
                enable_delay,
                functools.partial(
                    self.enable_buttons,
                    enable=True
                )
            )

    def enable_buttons(self, enable):
        self.ui.ok_button.setEnabled(enable)
        self.ui.cancel_button.setEnabled(enable)

    def ok(self):
        self.ok_action()

    def cancel(self):
        self.cancel_action()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
