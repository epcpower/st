#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtWidgets import QWidget, QStackedLayout, QLayout, QGridLayout, QSizePolicy


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
        self.stackedLayout = QStackedLayout()
        self.stackedLayout.addWidget(self.scale1)
        self.stackedLayout.addWidget(self.scale2)
        self.stackedLayout.setStackingMode(1)
        self.ui.glayout.addLayout(self.stackedLayout, 0, 0)

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