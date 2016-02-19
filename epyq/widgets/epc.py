#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from enum import Enum
import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, Q_ENUMS)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'




class Epc(epyq.widgets.abstractwidget.AbstractWidget):
    class MyEnum(Enum):
        first, second, third = range(3)

    Q_ENUMS(MyEnum)

    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'epc.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent)

        self._frame = None
        self._signal = None

        self._my_enum = self.MyEnum.second

    @pyqtProperty(MyEnum)
    def my_enum(self):
        return self._my_enum

    @my_enum.setter
    def my_enum(self, my_enum):
        self._my_enum = my_enum

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

        self.ui.value.setText(value)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
