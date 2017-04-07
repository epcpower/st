#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.listmenu
import functools
import io
import math
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QAbstractSlider
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QFile, QFileInfo, QTextStream,
                          QCoreApplication, QModelIndex)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ListMenuView(QtWidgets.QWidget):
    node_clicked = pyqtSignal(epyqlib.listmenu.Node)

    def __init__(self, parent=None, in_designer=False):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        ui = 'listmenuview.ui'
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

        scroll_bar = self.ui.list_view.verticalScrollBar()
        up = functools.partial(
            scroll_bar.triggerAction,
            QAbstractSlider.SliderPageStepSub
        )
        self.ui.up_button.clicked.connect(up)
        down = functools.partial(
            scroll_bar.triggerAction,
            QAbstractSlider.SliderPageStepAdd
        )
        self.ui.down_button.clicked.connect(down)

        self.ui.list_view.viewport().setAutoFillBackground(False)

        self.ui.list_view.clicked.connect(self.clicked)

    @pyqtSlot(QModelIndex)
    def clicked(self, index):
        if not index.isValid():
            return

        node = self.model.node_from_index(index)

        self.node_clicked.emit(node)

        # self.ui.module_to_nv_button.clicked.connect(self.module_to_nv)
        # self.ui.write_to_module_button.clicked.connect(self.write_to_module)
        # self.ui.read_from_module_button.clicked.connect(self.read_from_module)
        # self.ui.write_to_file_button.clicked.connect(self.write_to_file)
        # self.ui.read_from_file_button.clicked.connect(self.read_from_file)
        #
        # self.resize_columns = epyqlib.nv.Columns(
        #     name=True,
        #     value=True)

    def setModel(self, model):
        self.model = model
        self.node_clicked.connect(self.model.node_clicked)

        self.ui.list_view.setModel(self.model)

        self.ui.esc_button.clicked.connect(self.model.esc_clicked)
        self.root_changed(self.model.root)
        self.model.root_changed.connect(self.root_changed)

        # model.set_status_string.connect(self.set_status_string)

        # self.ui.module_to_nv.connect(model.module_to_nv)
        # self.ui.read_from_module.connect(model.read_from_module)
        # self.ui.write_to_module.connect(model.write_to_module)
        # self.ui.read_from_file.connect(model.read_from_file)
        # self.ui.write_to_file.connect(model.write_to_file)

        # self.ui.tree_view.header().setStretchLastSection(False)

        # for i in epyqlib.nv.Columns.indexes:
        #     if self.resize_columns[i]:
        #         self.ui.tree_view.header().setSectionResizeMode(
        #             i, QtWidgets.QHeaderView.ResizeToContents)
        # # TODO: would be nice to share between message and signal perhaps?
        # self.ui.tree_view.header().setSectionResizeMode(
        #     epyqlib.nv.Columns.indexes.value, QtWidgets.QHeaderView.Stretch)
        #
        # self.ui.tree_view.setItemDelegateForColumn(
        #     epyqlib.nv.Columns.indexes.value,
        #     epyqlib.delegates.Combo(model=model, parent=self))

    @pyqtSlot(epyqlib.listmenu.Node)
    def root_changed(self, node):
        self.ui.label.setText(node.fields.name)
        self.ui.list_view.scrollToTop()
        self.ui.esc_button.setDisabled(node.tree_parent is None)

    def set_padding(self, padding):
        self.setStyleSheet('''
            QListView::item
            {{
                padding: {}px;
            }}
        '''.format(padding))

    def update_calculated_layout(self):
        minimum_padding = 0
        self.set_padding(minimum_padding)

        view = self.ui.list_view
        model = self.model

        list = view.contentsRect().height()
        item = view.itemDelegate().sizeHint(
            view.viewOptions(),
            model.index_from_node(
                model.root)).height()
        most_items = math.floor(list / item)
        remainder = list % item
        padding = minimum_padding + (remainder / most_items) / 2
        self.set_padding(padding)

        for button in [self.ui.down_button,
                       self.ui.up_button,
                       self.ui.esc_button]:
            # TODO: CAMPid 98754713241621231778985432
            button.setMaximumWidth(button.height())

    def selected_text(self):
        indexes = self.ui.list_view.selectedIndexes()
        index = indexes[0]
        return index.internalPointer().fields.name

    def select_node(self, node):
        self.ui.list_view.setCurrentIndex(self.model.index_from_node(node))


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
