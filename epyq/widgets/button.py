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

    def set(self, value):
        value = str(value)
        self.widget_value_changed(value)
        # TODO: CAMPid 85478672616219005471279
        enum_string = self.signal_object.signal._values[value]
        text = self.signal_object.enumeration_format_re['format'].format(
            s=enum_string, v=value)
        self.ui.value.setText(text)

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
