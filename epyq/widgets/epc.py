#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstracttxwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, Qt)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Epc(epyq.widgets.abstracttxwidget.AbstractTxWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'epc.ui')

        epyq.widgets.abstracttxwidget.AbstractTxWidget.__init__(self,
                ui=ui_file, parent=parent)

        # TODO: CAMPid 398956661298765098124690765
        self.ui.value.editingFinished.connect(self.widget_value_changed)

        self._frame = None
        self._signal = None

    def widget_value_changed(self):
        epyq.widgets.abstracttxwidget.AbstractTxWidget.widget_value_changed(
            self, self.ui.value.text())

    def set_value(self, value):
        if self.signal_object is not None:
            if len(self.signal_object.enumeration) > 0:
                value = self.signal_object.full_string
            else:
                value = self.signal_object.format_float()
        elif value is None:
            # TODO: quit hardcoding this and it's better implemented elsewhere
            value = '{0:.2f}'.format(0)
        else:
            # TODO: quit hardcoding this and it's better implemented elsewhere
            value = '{0:.2f}'.format(value)

        self.ui.value.setText(value)

    @epyq.widgets.abstracttxwidget.AbstractTxWidget.tx.setter
    def tx(self, tx):
        epyq.widgets.abstracttxwidget.AbstractTxWidget.tx.fset(self, tx)

        self.ui.value.acceptsDrops = self.tx

        self.ui.value.setMouseTracking(self.tx)
        self.ui.value.setReadOnly(not self.tx)
        self.ui.value.setFocusPolicy(Qt.StrongFocus if self.tx else Qt.NoFocus)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
