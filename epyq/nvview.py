#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.nv
import io
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QFile, QFileInfo, QTextStream,
                          QCoreApplication)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class NvView(QtWidgets.QWidget):
    module_to_nv = pyqtSignal()
    read_from_module = pyqtSignal()
    write_to_module = pyqtSignal()
    read_from_file = pyqtSignal()
    write_to_file = pyqtSignal()

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        ui = 'nvview.ui'
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

        self.ui.module_to_nv_button.clicked.connect(self.module_to_nv)
        self.ui.write_to_module_button.clicked.connect(self.write_to_module)
        self.ui.read_from_module_button.clicked.connect(self.read_from_module)
        self.ui.write_to_file_button.clicked.connect(self.write_to_file)
        self.ui.read_from_file_button.clicked.connect(self.read_from_file)

        self.resize_columns = epyq.nv.Columns(
            name=True,
            value=True)

    def setModel(self, model):
        self.ui.tree_view.setModel(model)

        model.set_status_string.connect(self.set_status_string)

        self.ui.module_to_nv.connect(model.module_to_nv)
        self.ui.read_from_module.connect(model.read_from_module)
        self.ui.write_to_module.connect(model.write_to_module)
        self.ui.read_from_file.connect(model.read_from_file)
        self.ui.write_to_file.connect(model.write_to_file)

        self.ui.tree_view.header().setStretchLastSection(False)

        for i in epyq.nv.Columns.indexes:
            if self.resize_columns[i]:
                self.ui.tree_view.header().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)
        # TODO: would be nice to share between message and signal perhaps?
        self.ui.tree_view.header().setSectionResizeMode(
            epyq.nv.Columns.indexes.value, QtWidgets.QHeaderView.Stretch)

        self.ui.tree_view.setItemDelegateForColumn(
            epyq.nv.Columns.indexes.value,
            epyq.delegates.Combo(model=model, parent=self))

    @pyqtSlot(str)
    def set_status_string(self, string):
        self.ui.status_label.setText(string)
        # TODO: the long activities that need this should be reworked
        #       https://epc-phab.exana.io/T273
        QCoreApplication.processEvents()

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
