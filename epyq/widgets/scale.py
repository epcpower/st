#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import QFileInfo

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

    def set_value(self, value):
        self.ui.scale.setValue(value)

    def set_range(self, min=None, max=None):
        self.ui.scale.setRange(min=min, max=max)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
