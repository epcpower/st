#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class IoPoint(QWidget):
    def __init__(self, parent=None, in_designer=False):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'iopoint.ui')

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

        self.ui.status.in_designer = self.in_designer
        self.ui.set.in_designer = self.in_designer
        self.ui.override.in_designer = self.in_designer

        self.update_configuration()

    @pyqtProperty(bool)
    def tx(self):
        return self.ui.set.tx

    @tx.setter
    def tx(self, tx):
        self.ui.set.tx = bool(tx)
        self.ui.override.tx = bool(tx)

        self.update_configuration()

    @pyqtProperty(str)
    def label_override(self):
        return self.ui.status.label_override

    @label_override.setter
    def label_override(self, label):
        self.ui.status.label_override = label

        self.update_configuration()

        # TODO: if not empty then do something

    @pyqtProperty('QString')
    def status_signal_path_element_0(self):
        return self.ui.status.signal_path_element_0

    @status_signal_path_element_0.setter
    def status_signal_path_element_0(self, value):
        self.ui.status.signal_path_element_0 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def status_signal_path_element_1(self):
        return self.ui.status.signal_path_element_1

    @status_signal_path_element_1.setter
    def status_signal_path_element_1(self, value):
        self.ui.status.signal_path_element_1 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def status_signal_path_element_2(self):
        return self.ui.status.signal_path_element_2

    @status_signal_path_element_2.setter
    def status_signal_path_element_2(self, value):
        self.ui.status.signal_path_element_2 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def set_signal_path_element_0(self):
        return self.ui.set.signal_path_element_0

    @set_signal_path_element_0.setter
    def set_signal_path_element_0(self, value):
        self.ui.set.signal_path_element_0 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def set_signal_path_element_1(self):
        return self.ui.set.signal_path_element_1

    @set_signal_path_element_1.setter
    def set_signal_path_element_1(self, value):
        self.ui.set.signal_path_element_1 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def set_signal_path_element_2(self):
        return self.ui.set.signal_path_element_2

    @set_signal_path_element_2.setter
    def set_signal_path_element_2(self, value):
        self.ui.set.signal_path_element_2 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def override_signal_path_element_0(self):
        return self.ui.override.signal_path_element_0

    @override_signal_path_element_0.setter
    def override_signal_path_element_0(self, value):
        self.ui.override.signal_path_element_0 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def override_signal_path_element_1(self):
        return self.ui.override.signal_path_element_1

    @override_signal_path_element_1.setter
    def override_signal_path_element_1(self, value):
        self.ui.override.signal_path_element_1 = value
        self.update_configuration()

    @pyqtProperty('QString')
    def override_signal_path_element_2(self):
        return self.ui.override.signal_path_element_2

    @override_signal_path_element_2.setter
    def override_signal_path_element_2(self, value):
        self.ui.override.signal_path_element_2 = value
        self.update_configuration()

    def update_configuration(self):
        self.ui.set.setVisible(self.tx)
        self.ui.override.setVisible(self.tx)
        if self.tx:
            self.ui.set_label.show()
            self.ui.override_label.show()
        else:
            self.ui.set_label.hide()
            self.ui.override_label.hide()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
