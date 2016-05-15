#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import pyqtSignal, pyqtProperty, QFileInfo

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Scale(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'scale.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent)

        self._frame = None
        self._signal = None

        self.override_range = False
        self._min = 0
        self._max = 1

    def set_value(self, value):
        self.ui.scale.setValue(value)

    def set_range(self, min=None, max=None):
        if self.override_range:
            min = self.minimum
            max = self.maximum

        self.ui.scale.setRange(min=min, max=max)

    @pyqtProperty(bool)
    def override_range(self):
        return self._override_range

    @override_range.setter
    def override_range(self, override):
        self._override_range = float(override)

    @pyqtProperty(float)
    def minimum(self):
        return self._min

    @minimum.setter
    def minimum(self, min):
        self._min = float(min)

    @pyqtProperty(float)
    def maximum(self):
        return self._max

    @maximum.setter
    def maximum(self, max):
        self._max = float(max)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
