#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.mixins
import epyq.widgets.abstractwidget
import os
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty, QFileInfo
from PyQt5.QtGui import QColor

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

        self._breakpoints = [self._min + (self._max - self._min) * n
                             for n in [0.10, 0.25, 0.75, 0.90]]
        self._colors = [Qt.darkRed,
                        Qt.darkYellow,
                        Qt.darkGreen,
                        Qt.darkYellow,
                        Qt.darkRed]

        self._frame = None
        self._signal = None

        self.update_configuration()

    @pyqtProperty(float)
    def lower_red_breakpoint(self):
        return self._breakpoints[0]

    @lower_red_breakpoint.setter
    def lower_red_breakpoint(self, breakpoint):
        self._breakpoints[0] = breakpoint
        self.update_configuration()

    @pyqtProperty(float)
    def lower_yellow_breakpoint(self):
        return self._breakpoints[1]

    @lower_yellow_breakpoint.setter
    def lower_yellow_breakpoint(self, breakpoint):
        self._breakpoints[1] = breakpoint
        self.update_configuration()

    @pyqtProperty(float)
    def upper_yellow_breakpoint(self):
        return self._breakpoints[2]

    @upper_yellow_breakpoint.setter
    def upper_yellow_breakpoint(self, breakpoint):
        self._breakpoints[2] = breakpoint
        self.update_configuration()

    @pyqtProperty(float)
    def upper_red_breakpoint(self):
        return self._breakpoints[3]

    @upper_red_breakpoint.setter
    def upper_red_breakpoint(self, breakpoint):
        self._breakpoints[3] = breakpoint
        self.update_configuration()

    @pyqtProperty(QColor)
    def lower_red_color(self):
        return self._colors[0]

    @lower_red_color.setter
    def lower_red_color(self, color):
        self._colors[0] = color
        self.update_configuration()

    @pyqtProperty(QColor)
    def lower_yellow_color(self):
        return self._colors[1]

    @lower_yellow_color.setter
    def lower_yellow_color(self, color):
        self._colors[1] = color
        self.update_configuration()

    @pyqtProperty(QColor)
    def green_color(self):
        return self._colors[2]

    @green_color.setter
    def green_color(self, color):
        self._colors[2] = color
        self.update_configuration()

    @pyqtProperty(QColor)
    def upper_yellow_color(self):
        return self._colors[3]

    @upper_yellow_color.setter
    def upper_yellow_color(self, color):
        self._colors[3] = color
        self.update_configuration()

    @pyqtProperty(QColor)
    def upper_red_color(self):
        return self._colors[4]

    @upper_red_color.setter
    def upper_red_color(self, color):
        self._colors[4] = color
        self.update_configuration()

    def set_value(self, value):
        self.ui.scale.setValue(value)

    def set_range(self, min=None, max=None):
        if self.override_range:
            min = self.minimum
            max = self.maximum

        self.ui.scale.setRange(min=min, max=max)

    def set_unit_text(self, units):
        self.ui.units.setText('[{}]'.format(units))

    def update_configuration(self):
        self.ui.scale.setColorRanges(self._colors, self._breakpoints)

        self.repaint()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
