# import epyqlib.delegates
# import epyqlib.txrx
import io
import os
from PyQt5 import QtWidgets, uic
# from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import QFile, QFileInfo, QTextStream, Qt
from PyQt5.QtWidgets import QHeaderView

import epyqlib.pyqabstractitemmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class VariableSelectionView(QtWidgets.QWidget):
    def __init__(self, parent=None, in_designer=False):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = 'variableselectionview.ui'
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

    def set_model(self, model):
        self.ui.tree_view.setModel(model)
        model.setSortRole(epyqlib.pyqabstractitemmodel.UserRoles.sort)

        header = self.ui.tree_view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(header.ResizeToContents)

    def set_sorting_enabled(self, enabled):
        self.ui.tree_view.setSortingEnabled(enabled)

    def sort_by_column(self, column, order):
        self.ui.tree_view.sortByColumn(column, order)

    @property
    def model(self):
        return self.tree_view.model()
