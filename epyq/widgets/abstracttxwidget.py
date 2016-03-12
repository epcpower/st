#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
from PyQt5.QtCore import pyqtProperty

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractTxWidget(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, ui, parent=None):
        epyq.widgets.abstractwidget.AbstractWidget.__init__(self, ui, parent)

        self.tx = False

        self._period = None

    @pyqtProperty(bool)
    def tx(self):
        return self._tx

    @tx.setter
    def tx(self, tx):
        self._tx = bool(tx)

        if self.signal_object is not None:
            if self.tx:
                self.signal_object.frame.cyclic_request(self, self._period)
            else:
                self.signal_object.frame.cyclic_request(self, None)

        self.update_connection()
        self.ui.value.setDisabled(not self.tx)

    def set_signal(self, signal):
        if signal is not None:
            try:
                period = signal.frame.frame._attributes['GenMsgCycleTime']
            except KeyError:
                # TODO: a more specific exception?
                raise Exception(
                    'No CycleTime/GenMsgCycleTime configured for frame {}'
                        .format(signal.frame.frame._name))

            self._period = float(period) / 1000

        epyq.widgets.abstractwidget.AbstractWidget.set_signal(self, signal)

    def update_connection(self, signal=None):
        if signal is not self.signal_object:
            if self.signal_object is not None:
                self.signal_object.frame.cyclic_request(self, None)

            if signal is not None:
                signal.frame.cyclic_request(self, self._period)

        epyq.widgets.abstractwidget.AbstractWidget.update_connection(
                self, signal)

    def widget_value_changed(self, value):
        if self.signal_object is not None and self.tx:
            self.signal_object.set_human_value(value)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
