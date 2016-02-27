#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, Qt, QEvent,
                          QTimer)
from PyQt5.QtGui import QMouseEvent

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Toggle(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'toggle.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent)

        self.ui.value.installEventFilter(self)
        self.ui.value.valueChanged.connect(self.widget_value_changed)

        self._frame = None
        self._signal = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.send)

        self.tx = False

    @pyqtProperty(bool)
    def tx(self):
        return self._tx

    @tx.setter
    def tx(self, tx):
        self._tx = bool(tx)

        if self.tx:
            # TODO: get this period from somewhere
            self.timer.setInterval(200)
            self.timer.start()
        else:
            self.timer.stop()

        self.update_connection()
        self.ui.value.setDisabled(not self.tx)

    def update_connection(self, signal=None):
        if not self.tx:
            epyq.widgets.abstractwidget.AbstractWidget.update_connection(
                self, signal)

    def eventFilter(self, qobject, qevent):
        if isinstance(qevent, QMouseEvent) and self.tx:
            if (qevent.button() == Qt.LeftButton and
                        qevent.type() == QEvent.MouseButtonRelease):
                self.toggle_released()

            return True

        return False

    def set_value(self, value):
        # TODO: quit hardcoding this and it's better implemented elsewhere
        if self.signal_object is not None:
            value = bool(self.signal_object.value)
        elif value is None:
            value = False
        else:
            value = bool(value)

        self.ui.value.setSliderPosition(value)

    def toggle_released(self):
        if self.ui.value.sliderPosition():
            self.ui.value.setSliderPosition(False)
        else:
            self.ui.value.setSliderPosition(True)

    def set_signal(self, signal):
        if signal is not self.signal_object:
            if signal is not None:
                self.ui.off.setText(signal.signal._values['0'])
                self.ui.on.setText(signal.signal._values['1'])
                signal.value_changed.connect(self.signal_value_changed)
            else:
                self.ui.off.setText('-')
                self.ui.on.setText('-')
        epyq.widgets.abstractwidget.AbstractWidget.set_signal(self, signal)

    def widget_value_changed(self, value):
        if self.signal_object is not None:
            self.signal_object.set_human_value(value)

    def signal_value_changed(self, value):
        self.ui.value.setSliderPosition(bool(value))

    def send(self):
        # TODO: connect directly to the frame and remove this function?
        if self.signal_object is not None:
            self.signal_object.frame._send(update=True)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
