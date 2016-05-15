#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
import os

from PyQt5.QtCore import pyqtProperty, QFileInfo

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Led(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'led.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent)

        file = 'led.svg'

        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(file).isAbsolute():
            file = os.path.join(
                QFileInfo.absolutePath(QFileInfo(__file__)), file)
        else:
            file = file

        self._relative_height = 1

        self.ui.value.load(file)
        self.elements = {
            False: 'dim',
            True: 'bright'
        }
        self.ui.value.main_element = self.elements[False]
        height = self.relative_height * self.ui.label.height()
        ratio = self.ui.value.ratio()

        self.ui.value.setMaximumHeight(height)
        self.ui.value.setMaximumWidth(height / ratio)

        # TODO: shouldn't this be in AbstractWidget?
        self._frame = None
        self._signal = None

    @pyqtProperty(float)
    def relative_height(self):
        return self._relative_height

    @relative_height.setter
    def relative_height(self, multiplier):
        self._relative_height = multiplier

        height = self.relative_height * self.ui.label.height()
        ratio = self.ui.value.ratio()

        self.ui.value.setMaximumHeight(height)
        self.ui.value.setMinimumHeight(height)

        width = height / ratio
        self.ui.value.setMaximumWidth(width)
        self.ui.value.setMinimumWidth(width)

    def set_value(self, value):
        # TODO: quit hardcoding this and it's better implemented elsewhere
        if self.signal_object is not None:
            value = bool(self.signal_object.value)
        elif value is None:
            value = False
        else:
            value = bool(value)

        self.ui.value.main_element = self.elements[value]


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
