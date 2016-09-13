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

        self.has_units_label = hasattr(self.ui, 'units')

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

        expected_type = epyq.form.EpcForm
        while parent is not None:
            if isinstance(parent, expected_type):
                parent.update_widget(self)
                break
            else:
                parent = parent.parent()
        else:
            raise Exception(
                'No valid {} widget found while searching parents'.format(
                    expected_type.__class__.__name__
                ))

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

    def has_units_label_a(self):
        return self.has_units_label

    @pyqtProperty(bool)
    def units_visible(self):
        if self.has_units_label:
            return self.ui.units.isVisible()

        return False

    @units_visible.setter
    def units_visible(self, new_visible):
        if self.has_units_label:
            self.ui.units.setVisible(new_visible)
            self.update_metadata()

    # TODO: CAMPid 943989817913241236127998452684328
    def set_label(self, new_signal=None):
        label = None
        if len(self.label_override) > 0:
            label = self.label_override

        if label is None:
            label = self.set_label_custom(new_signal=new_signal)

        if label is None:
            try:
                label = new_signal.long_name
            except AttributeError:
                pass

        if label is None:
            try:
                label = new_signal.name
            except AttributeError:
                pass

        if label is None:
            label = '-'

        self.ui.label.setText(label)

        if not self.label_visible:
            # TODO: CAMPid 938914912312674213467977981547743
            try:
                layout = self.parent().layout()
            except AttributeError:
                pass
            else:
                if isinstance(layout, QtWidgets.QGridLayout):
                    index = layout.indexOf(self)
                    if index >= 0:
                        row, column, row_span, column_span = (
                            layout.getItemPosition(index)
                        )
                        # TODO: search in case of colspan
                        left = None
                        for offset in range(1, column + 1):
                            left_column = column - offset
                            left_layout_item = layout.itemAtPosition(
                                row, left_column)

                            if left_layout_item is not None:
                                left_temp = left_layout_item.widget()
                                left_index = layout.indexOf(left_temp)
                                _, _, _, column_span = layout.getItemPosition(
                                    left_index)

                                if left_temp is not None:
                                    if column_span < offset:
                                        break

                                    left = left_temp

                        if isinstance(left, QtWidgets.QLabel):
                            left.setText(label)

    def set_label_custom(self, new_signal=None):
        return None

    def set_units(self, units):
        if units is None:
            units = '-'

        self.set_unit_text(units)

        if not self.units_visible:
            # TODO: CAMPid 938914912312674213467977981547743
            try:
                layout = self.parent().layout()
            except AttributeError:
                pass
            else:
                if isinstance(layout, QtWidgets.QGridLayout):
                    index = layout.indexOf(self)
                    if index >= 0:
                        row, column, row_span, column_span = (
                            layout.getItemPosition(index)
                        )
                        right = layout.itemAtPosition(row, column + column_span)
                        if right is not None:
                            right = right.widget()
                            if isinstance(right, QtWidgets.QLabel):
                                right.setText(units)

    def set_unit_text(self, units):
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
            self.set_label(new_signal=signal)
            if signal is not None:
                self.set_units(signal.unit)
                self.set_value(None)
            else:
                self.set_units(None)

            self.update_tool_tip(new_signal=signal)

            self.update_connection(signal)
            self.signal_object = signal

            if signal is not None:
                self.set_range(min=float(signal.min),
                               max=float(signal.max))

                signal.force_value_changed()

    def update_tool_tip(self, new_signal=None):
        if len(self.tool_tip_override) > 0:
            tip = self.tool_tip_override
        elif new_signal is not None:
            tip = new_signal.comment
        else:
            tip = ''

        self.setToolTip(tip)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
