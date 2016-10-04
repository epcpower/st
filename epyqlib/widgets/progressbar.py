#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.abstractwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ProgressBar(epyqlib.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None, in_designer=False):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'progressbar.ui')

        epyqlib.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent, in_designer=in_designer)

        self._min = None
        self._max = None
        self._counts = 1000
        self.ui.progressBar.setRange(0, self._counts)

        self._frame = None
        self._signal = None

    def set_value(self, value):
        if value is None:
            value = 0

        if value >= 0:
            # TODO: fix this especially for positive and negative ranges
            counts = value - self._min
        elif value < 0:
            counts = abs(value) - abs(self._max)

        counts /= abs(self._max - self._min)
        counts *= self._counts
        self.ui.progressBar.setValue(int(round(counts)))
        # TODO: quit hardcoding this and it's better implemented elsewhere
        self.ui.progressBar.setFormat('{0:.2f}'.format(value))

    def set_range(self, min=None, max=None):
        if min * max < 0:
            # opposite signs and neither is zero
            # TODO: pick the right exception
            raise Exception('Signs must match or one limit be zero')
        elif min == max:
            # TODO: pick the right exception
            raise Exception('Min and max may not be the same')
        elif min > max:
            # TODO: pick the right exception
            raise Exception('Min must be less than max')

        self._min = min
        self._max = max
        self.ui.progressBar.setInvertedAppearance(self._min < 0)
        # self.ui.progressBar.setRange(self._min, self._max)



if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
