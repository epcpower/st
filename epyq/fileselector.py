#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import io
import os
from PyQt5 import QtCore, QtWidgets, QtGui, uic, Qt
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                            pyqtSlot, QTimer)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QListWidgetItem,
                             QFileDialog)
from PyQt5.QtGui import QPixmap
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'

# TODO: CAMPid 9756562638416716254289247326327819
class Selector(QtWidgets.QDialog):
    def __init__(self, recent=[], parent=None):
        QtWidgets.QDialog.__init__(self, parent=parent)
        self.setWindowFlags(QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint)

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        self.setWindowIcon(ico)

        ui = 'fileselector.ui'
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

        self.setWindowTitle('Recent Files')

        for file in recent:
            self.ui.list.addItem(file)

        self.ui.list.itemSelectionChanged.connect(self.changed)
        self.ui.open.setDisabled(True)

        self.ui.list.itemDoubleClicked.connect(self.double_clicked)
        self.ui.browse.clicked.connect(self.browse_button)
        self.ui.open.clicked.connect(self.accept)
        self.ui.quit.clicked.connect(self.reject)

        self.selected_string = ''

    @pyqtSlot()
    def browse_button(self):
        # TODO: CAMPid 97456612391231265743713479129
        can_file = QFileDialog.getOpenFileName(
                filter='PCAN Symbol (*.sym);; All File (*)',
                initialFilter='PCAN Symbol (*.sym)')[0]
        if len(can_file) == 0:
            return

        self.ui.list.clearSelection()
        self.ui.selected_edit.setText(can_file)
        self.selected_string = can_file
        self.ui.open.setDisabled(False)

    @pyqtSlot()
    def reject(self):
        self.selected_string = ''

        QtWidgets.QDialog.reject(self)

    @pyqtSlot(QListWidgetItem)
    def double_clicked(self, item):
        self.accept()

    def changed(self):
        if len(self.ui.list.selectedItems()) == 1:
            self.selected_string = self.ui.list.currentItem().text()
        else:
            self.selected_string = ''

        self.ui.open.setDisabled(self.selected_string is '')
        self.ui.selected_edit.setText(self.selected_string)

    def selected(self):
        return self.selected_string


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
