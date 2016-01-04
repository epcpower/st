import epyq.txrx
import os
from PyQt5 import QtWidgets, uic

# See file COPYING in this source tree
__copyright__ = 'Copyright 2015, EPC Power Corp.'
__license__ = 'GPLv2+'


class TxRxView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'txrxview.ui')
        self.ui = uic.loadUi(ui_file, self)

        self.resize_columns = epyq.txrx.Columns(
            id=True,
            message=True,
            signal=True,
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
        # TODO: would be nice to share between message and signal perhaps?
        self.ui.tree_view.header().setSectionResizeMode(
            epyq.txrx.Columns.indexes.message, QtWidgets.QHeaderView.Stretch)

        self.ui.tree_view.setItemDelegateForColumn(
            epyq.txrx.Columns.indexes.value,
            epyq.txrx.ValueDelegate(model=model, parent=self))
