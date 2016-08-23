#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import canmatrix.importany as importany
import epyq.canneo
import io
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, QEvent)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


event_type_to_name = {
    getattr(QEvent, t): t for t in dir(QEvent)
    if isinstance(getattr(QEvent, t), QEvent.Type)
}

class AbstractWidget(QtWidgets.QWidget):
    def __init__(self, ui, parent=None, in_designer=False):
        self.in_designer = in_designer
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
        self._tool_tip_override = ''

        self.set_signal(force_update=True)

        self._frame = ''
        self._signal = ''

    def changeEvent(self, event):
        QtWidgets.QWidget.changeEvent(self, event)
        if event.type() == QEvent.ParentChange:
            self.update_metadata()

    def update_metadata(self):
        if not self.in_designer:
            return

        parent = self

        self.set_signal(force_update=True)

        while parent is not None:
            name = 'can_file'
            if name in parent.dynamicPropertyNames():
                can_file = parent.property(name)
                break
            else:
                parent = parent.parent()
        else:
            return

        try:
            matrix = list(importany.importany(can_file).values())[0]
            neo = epyq.canneo.Neo(matrix=matrix)

            frame_name = self.property('frame')
            signal_name = self.property('signal')

            self.set_range(min=0, max=100)
            self.set_value(42)

            # TODO: add some notifications
            frame = neo.frame_by_name(frame_name)
            if frame is not None:
                signal = frame.signal_by_name(signal_name)
                if signal is not None:
                    self.set_signal(signal)
        except:
            pass

    @pyqtProperty('QString')
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame
        self.update_metadata()

    @pyqtProperty('QString')
    def signal(self):
        return self._signal

    @signal.setter
    def signal(self, signal):
        self._signal = signal
        self.update_metadata()

    @pyqtProperty('QString')
    def label_override(self):
        return self._label_override

    @label_override.setter
    def label_override(self, new_label_override):
        self._label_override = str(new_label_override)
        self.ui.label.setText(self.label_override)
        self.update_metadata()

    @pyqtProperty('QString')
    def tool_tip_override(self):
        return self._tool_tip_override

    @tool_tip_override.setter
    def tool_tip_override(self, new_tool_tip_override):
        self._tool_tip_override = str(new_tool_tip_override)
        self.update_tool_tip()
        self.update_metadata()

    @pyqtProperty(bool)
    def label_visible(self):
        return self.ui.label.isVisible()

    @label_visible.setter
    def label_visible(self, new_visible):
        self.ui.label.setVisible(new_visible)
        self.update_metadata()

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

    def set_signal(self, signal=None, force_update=False):
        if signal is not self.signal_object or force_update:
            if signal is not None:
                label = signal.long_name
                if label is None:
                    label = signal.name

                self.set_label(label)
                self.set_units(signal.unit)
                self.set_value(None)
            else:
                self.set_label(None)
                self.set_units(None)

            self.update_tool_tip()

            self.update_connection(signal)
            self.signal_object = signal

            if signal is not None:
                self.set_range(min=float(signal.min),
                               max=float(signal.max))

                signal.force_value_changed()

    def update_tool_tip(self):
        if len(self.tool_tip_override) > 0:
            tip = self.tool_tip_override
        elif self.signal_object is not None:
            tip = signal_object.comment
        else:
            tip = ''

        self.setToolTip(tip)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
