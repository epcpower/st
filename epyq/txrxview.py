import epyq.delegates
import epyq.txrx
import io
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import QFile, QFileInfo, QTextStream

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class TxRxView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        ui = 'txrxview.ui'
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

        self.resize_columns = epyq.txrx.Columns.fill(False)

    def setModel(self, model):
        self.ui.tree_view.setModel(model)

        self.ui.tree_view.header().setStretchLastSection(False)

        for i in epyq.txrx.Columns.indexes:
            if self.resize_columns[i]:
                self.ui.tree_view.header().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)
            else:
                # at least fit the column headers and/or initial data
                self.ui.tree_view.resizeColumnToContents(i)

        self.ui.tree_view.header().setSectionResizeMode(
            epyq.txrx.Columns.indexes.name, QtWidgets.QHeaderView.Stretch)

        self.ui.tree_view.setItemDelegateForColumn(
            epyq.txrx.Columns.indexes.value,
            epyq.delegates.Combo(model=model, parent=self))

        self.ui.tree_view.setColumnWidth(epyq.txrx.Columns.indexes.value,
                                         self.calculate_max_value_width())
        self.ui.tree_view.setColumnWidth(epyq.txrx.Columns.indexes.id,
                                         self.calculate_max_id_width() +
                                         self.ui.tree_view.indentation())

    # TODO: CAMPid 989849193479134917954791341
    def calculate_max_value_width(self):
        metric = self.ui.tree_view.fontMetrics()
        chars = ['{:X}'.format(i) for i in range(16)]
        widths = [metric.width(c) for c in chars]
        widest_width = max(widths)
        widest_char = chars[widths.index(widest_width)]
        string = ' '.join([widest_char * 2] * 8)
        return metric.width(string)

    # TODO: CAMPid 989849193479134917954791341
    def calculate_max_id_width(self):
        metric = self.ui.tree_view.fontMetrics()
        chars = ['{:X}'.format(i) for i in range(16)]
        widths = [metric.width(c) for c in chars]
        widest_width = max(widths)
        widest_char = chars[widths.index(widest_width)]
        string = '0x{}'.format(widest_char * 8)
        return metric.width(string)
