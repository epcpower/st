#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.mixins
import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import pyqtSignal, pyqtProperty, QFileInfo

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Scale(epyq.widgets.abstractwidget.AbstractWidget,
            epyq.mixins.OverrideRange):
    def __init__(self, parent=None, in_designer=False):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'scale.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent, in_designer=in_designer)

        epyq.mixins.OverrideRange.__init__(self)

        self._frame = None
        self._signal = None

    def set_value(self, value):
        self.ui.scale.setValue(value)

    def set_range(self, min=None, max=None):
        if self.override_range:
            min = self.minimum
            max = self.maximum

        self.ui.scale.setRange(min=min, max=max)

    def set_unit_text(self, units):
        self.ui.units.setText('[{}]'.format(units))


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
