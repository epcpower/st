#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.listmenu
import functools
import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ListSelect(QWidget):
    def __init__(self, parent=None, in_designer=False, action=None):
        QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'listselect.ui')

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

        self.action = action
        self.items = {}
        self.ui.accept_button.clicked.connect(self.accept)
        self.ui.cancel_button.clicked.connect(
            functools.partial(self.exit, value=None))

    def focus(self, value, action, items, label=''):
        self.items = items
        root = epyqlib.listmenu.Node(text=label)
        model = epyqlib.listmenu.ListMenuModel(root=root)
        self.ui.menu_view.setModel(model)

        selected = None

        for key, item_value in sorted(self.items.items()):
            node = epyqlib.listmenu.Node(text=item_value, action=lambda: None)
            root.append_child(node)

            if key == int(value):
                selected = node

        if selected is not None:
            self.ui.menu_view.select_node(selected)

        self.action = action
        parent = self.parent()
        if hasattr(parent, 'setCurrentWidget'):
            parent.setCurrentWidget(self)
        focused_widget = self.focusWidget()
        if focused_widget is not None:
            focused_widget.clearFocus()

    def accept(self):
        selected = self.ui.menu_view.selected_text()
        found_key = None
        for key, value in self.items.items():
            if value == selected:
                found_key = key
                break

        self.exit(value=found_key)

    def exit(self, value):
        self.action(value=value)

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
