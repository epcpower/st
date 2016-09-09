#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget

from PyQt5.QtCore import pyqtProperty, pyqtSignal, QEvent, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractTxWidget(epyq.widgets.abstractwidget.AbstractWidget):
    edit = pyqtSignal(QWidget, QWidget)

    def __init__(self, ui, parent=None, in_designer=False):
        epyq.widgets.abstractwidget.AbstractWidget.__init__(
            self, ui=ui, parent=parent, in_designer=in_designer)

        self.tx = False

        for widget in self.findChildren(QWidget):
            if widget.property('editable_click'):
                widget.installEventFilter(self)

        self._period = None

    @pyqtProperty(bool)
    def tx(self):
        return self._tx

    @tx.setter
    def tx(self, tx):
        self._tx = bool(tx)

        self.set_signal(signal=self.signal_object)
        self.ui.value.setDisabled(not self.tx)

    def eventFilter(self, qobject, qevent):
        if (isinstance(qevent, QMouseEvent)
                and self.tx
                and qevent.button() == Qt.LeftButton
                and qevent.type() == QEvent.MouseButtonRelease
                and qobject.rect().contains(qevent.localPos().toPoint())):
            self.edit.emit(self, self)

            return True

        return False

    def set_signal(self, signal=None, force_update=False):
        if signal is not None and self.tx:
            period = signal.frame.cycle_time
            if period is None:
                self._period = None
            else:
                self._period = float(period) / 1000
        else:
            self._period = None

        epyq.widgets.abstractwidget.AbstractWidget.set_signal(
            self, signal, force_update=force_update)

    def update_connection(self, signal=None):
        if signal is not self.signal_object:
            if self.signal_object is not None:
                self.signal_object.frame.cyclic_request(self, None)

            if signal is not None and self.tx and self._period is not None:
                signal.frame.cyclic_request(self, self._period)

        epyq.widgets.abstractwidget.AbstractWidget.update_connection(
                self, signal)

    def widget_value_changed(self, value):
        if self.signal_object is not None and self.tx:
            self.signal_object.set_human_value(value)

            if self._period is None:
                self.signal_object.frame.send_now()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
