#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, QTimer)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Enum(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'enum.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent)

        # TODO: CAMPid 398956661298765098124690765
        self.ui.value.currentTextChanged.connect(self.widget_value_changed)

        self._frame = None
        self._signal = None

        # TODO: CAMPid 398956661298765098124690765
        self.timer = QTimer()
        self.timer.timeout.connect(self.send)

        # TODO: CAMPid 398956661298765098124690765
        self.tx = False

    # TODO: CAMPid 398956661298765098124690765
    @pyqtProperty(bool)
    def tx(self):
        return self._tx

    # TODO: CAMPid 398956661298765098124690765
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

    # TODO: CAMPid 398956661298765098124690765
    def update_connection(self, signal=None):
        if not self.tx:
            epyq.widgets.abstractwidget.AbstractWidget.update_connection(
                self, signal)

    def set_value(self, value):
        if self.signal_object is not None:
            if len(self.signal_object.signal._values) > 0:
                value = self.signal_object.full_string
            else:
                value = self.signal_object.format_float()
        elif value is None:
            value = '-'
        else:
            # TODO: quit hardcoding this and it's better implemented elsewhere
            value = '{0:.2f}'.format(value)

        self.ui.value.setCurrentText(value)

    def set_signal(self, signal):
        if signal is not self.signal_object:
            self.ui.value.clear()
            if signal is not None:
                full_strings = []
                # TODO: CAMPid 94562754956589992752348667
                for value in sorted(signal.signal._values.keys()):
                    enum_string = signal.signal._values[value]
                    full_strings.append(signal.enumeration_format_re['format'].format(
                        s=enum_string, v=value))

                self.ui.value.addItems(full_strings)

        epyq.widgets.abstractwidget.AbstractWidget.set_signal(self, signal)

    # TODO: CAMPid 398956661298765098124690765
    def widget_value_changed(self, value):
        if self.signal_object is not None and self.tx:
            self.signal_object.set_human_value(value)

    # TODO: CAMPid 398956661298765098124690765
    def signal_value_changed(self, value):
        self.ui.value.setSliderPosition(bool(value))

    # TODO: CAMPid 398956661298765098124690765
    def send(self):
        # TODO: connect directly to the frame and remove this function?
        if self.signal_object is not None:
            self.signal_object.frame._send(update=True)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
