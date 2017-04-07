#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import functools
import io
import os
import textwrap
import time

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ParameterEdit(QWidget):
    def __init__(self, parent=None, in_designer=False, edit=None, nv=None,
                 dialog=None, esc_action=None):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'parameteredit.ui')

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

        self._edit = edit
        self._dialog = dialog
        self.nv = nv

        self.ui.to_device.set_signal(self.nv)
        self.nv.status_signal.value_changed.connect(self.nv.value_changed)

        self.ui.save_to_nv_button.clicked.connect(self.save_to_nv)

        self.ui.to_device.edited.connect(self.edited)

        self.ui.description.setText(self.ui.to_device.toolTip())

        self.esc_action = esc_action
        self.ui.esc_button.clicked.connect(self.esc)

    def esc(self, checked):
        if self.esc_action is not None:
            self.esc_action()

    def edited(self, value):
        self.nv.read_from_device()
        time.sleep(0.05)
        self.nv.set_human_value(value)
        self.nv.write_to_device()

    def save_to_nv(self):
        focus_self = functools.partial(
            self.parent().setCurrentWidget,
            self
        )

        # TODO: CAMPid 93849811216123127753953680713426
        def inverter_to_nv():
            self.nv.tree_parent.module_to_nv()
            focus_self()

        self._dialog.focus(ok_action=inverter_to_nv,
                         cancel_action=focus_self,
                         label=textwrap.dedent('''\
                             Save all parameters to NV?''')
                         )

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
