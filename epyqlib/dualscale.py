#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtWidgets import QWidget, QStackedLayout, QLayout 
from PyQt5.QtGui import QColor


import epyqlib.widgets.scale

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'

class DualScale(QWidget):

    def __init__(self, parent=None, in_designer=False):

        QWidget.__init__(self, parent = parent)

        self.in_designer = in_designer

        self.d_vertically_flipped = False


        ui = self.getPath()

        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(ui).isAbsolute():
            ui_file = os.path.join(
                QFileInfo.absolutePath(QFileInfo(__file__)), ui)
        else:
            ui_file = ui
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly | QFile.Text)
        ts = QTextStream(ui_file)
        sio = io.StringIO(ts.readAll())
        self.ui = uic.loadUi(sio, self)

        self.scale1 = epyqlib.widgets.scale.Scale(self, in_designer)
        self.scale2 = epyqlib.widgets.scale.Scale(self, in_designer)
        # color ranges, scale markers, labels, needle painted.
        self.scale1.scale.m_paintMode = 1
        # needle, cover painted.
        self.scale2.scale.m_paintMode = 3
        # scale2's needle is blue
        self.scale2.scale.isBlue = True
        self.stackedLayout = QStackedLayout()
        self.stackedLayout.addWidget(self.scale2)
        self.stackedLayout.addWidget(self.scale1)
        self.stackedLayout.setStackingMode(1)
        self.ui.glayout.addLayout(self.stackedLayout, 0, 0)

        # Trying to figure out how to get lower min and the higher max and change the scale
        # true_min = min(self.scale1.ui.scale.m_minimum, self.scale2.ui.scale.m_minimum)
        # true_max = max(self.scale1.ui.scale.m_maximum, self.scale2.ui.scale.m_maximum)

        # self.scale1.minimum = true_min
        # self.scale2.minimum = true_min

        # self.scale1.maximum = true_max
        # self.scale2.maximum = true_max

        # self.scale1.override_range = True
        # self.scale2.override_range = True

    def getPath(self):
        return os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'dualscale.ui')

    @pyqtProperty('QString')
    def scale1_signal_path(self):
        return self.scale1.signal_path

    @scale1_signal_path.setter
    def scale1_signal_path(self, value):
        self.scale1.signal_path = value

    @pyqtProperty(bool)
    def scale1_label_visible(self):
        return self.scale1.label_visible

    @scale1_label_visible.setter
    def scale1_label_visible(self, new_visible):
        self.scale1.label_visible = new_visible


    @pyqtProperty('QString')
    def scale2_signal_path(self):
        return self.scale2.signal_path

    @scale2_signal_path.setter
    def scale2_signal_path(self, value):
        self.scale2.signal_path = value

    @pyqtProperty(bool)
    def scale2_label_visible(self):
        return self.scale2.label_visible

    @scale2_label_visible.setter
    def scale2_label_visible(self, new_visible):
        self.scale2.label_visible = new_visible

    @pyqtProperty(bool)
    def d_flipped(self):
        return self.d_vertically_flipped

    @d_flipped.setter
    def d_flipped(self, value):
        self.d_vertically_flipped = value
        self.scale1.s_flipped = value
        self.scale2.s_flipped = value



    @pyqtProperty(float)
    def lower_red_breakpoint(self):
        return self.scale1._breakpoints[0]

    @lower_red_breakpoint.setter
    def lower_red_breakpoint(self, breakpoint):
        self.scale1._breakpoints[0] = breakpoint
        self.scale1.update_configuration()

    @pyqtProperty(float)
    def lower_yellow_breakpoint(self):
        return self.scale1._breakpoints[1]

    @lower_yellow_breakpoint.setter
    def lower_yellow_breakpoint(self, breakpoint):
        self.scale1._breakpoints[1] = breakpoint
        self.scale1.update_configuration()

    @pyqtProperty(float)
    def upper_yellow_breakpoint(self):
        return self.scale1._breakpoints[2]

    @upper_yellow_breakpoint.setter
    def upper_yellow_breakpoint(self, breakpoint):
        self.scale1._breakpoints[2] = breakpoint
        self.scale1.update_configuration()

    @pyqtProperty(float)
    def upper_red_breakpoint(self):
        return self.scale1._breakpoints[3]

    @upper_red_breakpoint.setter
    def upper_red_breakpoint(self, breakpoint):
        self.scale1._breakpoints[3] = breakpoint
        self.scale1.update_configuration()

    @pyqtProperty(QColor)
    def lower_red_color(self):
        return self.scale1._colors[0]

    @lower_red_color.setter
    def lower_red_color(self, color):
        self.scale1._colors[0] = color
        self.scale1.update_configuration()

    @pyqtProperty(QColor)
    def lower_yellow_color(self):
        return self.scale1._colors[1]

    @lower_yellow_color.setter
    def lower_yellow_color(self, color):
        self.scale1._colors[1] = color
        self.scale1.update_configuration()

    @pyqtProperty(QColor)
    def green_color(self):
        return self.scale1._colors[2]

    @green_color.setter
    def green_color(self, color):
        self.scale1._colors[2] = color
        self.scale1.update_configuration()

    @pyqtProperty(QColor)
    def upper_yellow_color(self):
        return self.scale1._colors[3]

    @upper_yellow_color.setter
    def upper_yellow_color(self, color):
        self.scale1._colors[3] = color
        self.scale1.update_configuration()

    @pyqtProperty(QColor)
    def upper_red_color(self):
        return self.scale1._colors[4]

    @upper_red_color.setter
    def upper_red_color(self, color):
        self.scale1._colors[4] = color
        self.scale1.update_configuration()
 