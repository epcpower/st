import epyq.delegates
import epyq.txrx
import io
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QFile, QFileInfo, QTextStream

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class TxRxView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # TODO: CAMPid 9549757292917394095482739548437597676742
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'txrxview.ui')
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly | QFile.Text)
        ts = QTextStream(ui_file)
        sio = io.StringIO(ts.readAll())
        self.ui = uic.loadUi(sio, self)

        self.resize_columns = epyq.txrx.Columns(
            id=True,
            name=True,
            length=True,
            value=False,
            dt=False)

    def setModel(self, model):
        self.ui.tree_view.setModel(model)

        self.ui.tree_view.header().setStretchLastSection(False)

        for i in epyq.txrx.Columns.indexes:
            if self.resize_columns[i]:
                self.ui.tree_view.header().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)
        self.ui.tree_view.header().setSectionResizeMode(
            epyq.txrx.Columns.indexes.name, QtWidgets.QHeaderView.Stretch)

        self.ui.tree_view.setItemDelegateForColumn(
            epyq.txrx.Columns.indexes.value,
            epyq.delegates.Combo(model=model, parent=self))
