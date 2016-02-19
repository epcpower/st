#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractWidget(QtWidgets.QWidget):
    def __init__(self, ui, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # TODO: CAMPid 9549757292917394095482739548437597676742
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), ui)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly | QFile.Text)
        ts = QTextStream(ui_file)
        sio = io.StringIO(ts.readAll())
        self.ui = uic.loadUi(sio, self)

        self.signal_object = None

    @pyqtProperty('QString')
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame

    @pyqtProperty('QString')
    def signal(self):
        return self._signal

    @signal.setter
    def signal(self, signal):
        self._signal = signal

    def set_label(self, value):
        self.ui.label.setText(value + ':')

    def set_full_string(self, string):
        pass

    def set_range(self, min=None, max=None):
        pass

    def set_signal(self, signal):
        if signal is not self.signal:
            if signal is not None:
                if self.signal_object is not None:
                    self.signal_object.value_changed.disconnect(self.set_value)
                signal.value_changed.connect(self.set_value)

            self.signal_object = signal

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
