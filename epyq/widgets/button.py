#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstracttxwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, Qt, QEvent,
                          QTimer)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Button(epyq.widgets.abstracttxwidget.AbstractTxWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'button.ui')

        epyq.widgets.abstracttxwidget.AbstractTxWidget.__init__(self,
                ui=ui_file, parent=parent)

        # TODO: CAMPid 398956661298765098124690765
        self.ui.value.pressed.connect(self.pressed)
        self.ui.value.released.connect(self.released)

        self._frame = None
        self._signal = None

    def set_signal(self, signal):
        epyq.widgets.abstracttxwidget.AbstractTxWidget.set_signal(self, signal)

        if signal is not None:
            self.set(0)

            def get_text_width(widget, text):
                return widget.fontMetrics().boundingRect(text).width()

            button = self.ui.value
            # TODO: it would be nice to use the 'normal' extra width
            # initial_margin = button.width() - get_text_width(button,
            #                                                  button.text())

            widths = []
            for text in [self.calculate_text(v) for v in
                         self.signal_object.enumeration]:
                widths.append(get_text_width(button, text))

            button.setMinimumWidth(1.3 * max(widths))
        else:
            self.ui.value.setText('')

    def set(self, value):
        self.widget_value_changed(value)
        self.set_text(value)

    def calculate_text(self, value):
        # TODO: CAMPid 85478672616219005471279
        try:
            enum_string = self.signal_object.enumeration[value]
            text = self.signal_object.enumeration_format_re['format'].format(
                s=enum_string, v=value)
        except (AttributeError, KeyError):
            text = str(value)

        return text

    def set_text(self, value):
        self.ui.value.setText(self.calculate_text(value))

    def pressed(self):
        self.set(1)

    def released(self):
        self.set(0)

    def set_value(self, value):
        # TODO  exception?
        pass


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
