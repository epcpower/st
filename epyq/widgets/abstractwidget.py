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

        self.signal_object = None

        self._label_override = ''

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

    @pyqtProperty('QString')
    def label_override(self):
        return self._label_override

    @label_override.setter
    def label_override(self, new_label_override):
        self._label_override = str(new_label_override)
        self.ui.label.setText(self.label_override)

    @pyqtProperty(bool)
    def label_visible(self):
        return self.ui.label.isVisible()

    @label_visible.setter
    def label_visible(self, new_visible):
        self.ui.label.setVisible(new_visible)

    def set_label(self, value):
        if len(self.label_override) > 0:
            value = self.label_override
        else:
            if value is None:
                value = '-'

        self.ui.label.setText(value)

    def set_units(self, units):
        if units is None:
            units = '-'

        try:
            widget = self.ui.units
        except AttributeError:
            pass
        else:
            widget.setText(units)

    def set_full_string(self, string):
        pass

    def set_range(self, min=None, max=None):
        pass

    def update_connection(self, signal=None):
        if signal is not self.signal_object:
            if self.signal_object is not None:
                self.signal_object.value_changed.disconnect(self.set_value)

            if signal is not None:
                signal.value_changed.connect(self.set_value)

    def set_signal(self, signal):
        if signal is not self.signal_object:
            if signal is not None:
                label = signal.long_name
                if label is None:
                    label = signal.name

                self.set_label(label)
                self.set_units(signal.unit)
                self.set_value(None)

                self.setToolTip(signal.comment)
            else:
                self.set_label(None)
                self.set_units(None)
                self.setToolTip('')

            self.update_connection(signal)
            self.signal_object = signal

            if signal is not None:
                self.set_range(min=float(signal.min),
                               max=float(signal.max))

            signal.force_value_changed()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
