#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.abstractwidget
import textwrap

from PyQt5.QtCore import pyqtProperty, pyqtSignal, QEvent, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QMessageBox, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractTxWidget(epyqlib.widgets.abstractwidget.AbstractWidget):
    edit = pyqtSignal(QWidget, QWidget)
    edited = pyqtSignal(float)

    def __init__(self, ui, parent=None, in_designer=False):
        epyqlib.widgets.abstractwidget.AbstractWidget.__init__(
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

    def meta_set_value(self, value):
        if not self.value.hasFocus():
            self.set_value(value)

    def user_set_value(self, value):
        self.signal_object.set_human_value(value, check_range=True)
        self.edited.emit(value)

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
            signal.frame.user_send_control = False
            period = signal.frame.cycle_time
            if period is None:
                self._period = None
            else:
                self._period = float(period) / 1000
        else:
            self._period = None

        epyqlib.widgets.abstractwidget.AbstractWidget.set_signal(
            self, signal, force_update=force_update)

    def update_connection(self, signal=None):
        if signal is not self.signal_object:
            if self.signal_object is not None:
                self.signal_object.frame.cyclic_request(self, None)

            if signal is not None and self.tx and self._period is not None:
                signal.frame.cyclic_request(self, self._period)

        epyqlib.widgets.abstractwidget.AbstractWidget.update_connection(
                self, signal)

    def widget_value_changed(self, value):
        if self.signal_object is not None and self.tx:
            try:
                self.signal_object.set_human_value(value, check_range=True)
            except epyqlib.canneo.OutOfRangeError as e:
                message = textwrap.dedent('''\
                Frame: {frame}
                Signal: {signal}

                Error: {error}
                ''').format(frame=self.signal_object.frame.name,
                            signal=self.signal_object.name,
                            error=str(e))

                epyqlib.utils.qt.dialog(
                    parent=self,
                    message=message,
                    icon=QMessageBox.Critical,
                )
            else:
                if self._period is None:
                    self.signal_object.frame.send_now()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
