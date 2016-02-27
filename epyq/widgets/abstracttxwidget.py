#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
from PyQt5.QtCore import pyqtProperty, QTimer

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractTxWidget(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, ui, parent=None):
        epyq.widgets.abstractwidget.AbstractWidget.__init__(self, ui, parent)

        # TODO: move this timer stuff to somewhere that the widgets don't
        #       double up on it
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
        epyq.widgets.abstractwidget.AbstractWidget.update_connection(
                self, signal)

    def widget_value_changed(self, value):
        if self.signal_object is not None and self.tx:
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
