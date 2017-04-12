#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.nv
import functools
import io
import os
import twisted.internet.defer
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QFile, QFileInfo, QTextStream,
                          QCoreApplication, Qt, QItemSelectionModel,
                          QModelIndex)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class NvView(QtWidgets.QWidget):
    module_to_nv = pyqtSignal()
    read_from_file = pyqtSignal()
    write_to_file = pyqtSignal()

    def __init__(self, parent=None, in_designer=False):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

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

        self.ui.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_view.customContextMenuRequested.connect(
            self.context_menu
        )

        self.resize_columns = epyqlib.nv.Columns(
            name=True,
            value=True,
            min=True,
            max=True,
            factory=True,
    )

        self.ui.tree_view.clicked.connect(self.clicked)

    def write_to_module(self):
        model = self.ui.tree_view.model()
        only_these = [nv for nv in model.root.children
                      if nv.value is not None]
        model.root.write_all_to_device(callback=self.update_signals,
                                       only_these = only_these)

    def read_from_module(self):
        model = self.ui.tree_view.model()
        model.root.read_all_from_device(callback=self.update_signals)

    def setModel(self, model):
        self.ui.tree_view.setModel(model)

        model.set_status_string.connect(self.set_status_string)

        self.ui.module_to_nv.connect(model.module_to_nv)

        read_from_file = functools.partial(
            model.read_from_file,
            parent=self
        )
        self.ui.read_from_file.connect(read_from_file)

        write_to_file = functools.partial(
            model.write_to_file,
            parent=self
        )
        self.ui.write_to_file.connect(write_to_file)

        self.ui.tree_view.header().setStretchLastSection(False)

        for i in epyqlib.nv.Columns.indexes:
            if self.resize_columns[i]:
                self.ui.tree_view.header().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)
        # TODO: would be nice to share between message and signal perhaps?
        self.ui.tree_view.header().setSectionResizeMode(
            epyqlib.nv.Columns.indexes.value, QtWidgets.QHeaderView.Stretch)

        self.ui.tree_view.setItemDelegateForColumn(
            epyqlib.nv.Columns.indexes.value,
            epyqlib.delegates.ByFunction(model=model, parent=self)
        )
        self.ui.tree_view.selectionModel().currentChanged.connect(
            self._current_changed)
        self.ui.tree_view.setSelectionMode(self.ui.tree_view.MultiSelection)

        self.ui.tree_view.setColumnHidden(
            epyqlib.nv.Columns.indexes.factory,
            all(len(nv.fields.factory) == 0 for nv in model.root.children)
        )

        model.force_action_decorations = True
        decoration_only_columns = (
            model.headers.indexes.clear,
            model.headers.indexes.reset
        )
        for column in decoration_only_columns:
            self.ui.tree_view.resizeColumnToContents(column)
            self.ui.tree_view.header().setSectionResizeMode(
                column, QtWidgets.QHeaderView.Fixed)
        model.force_action_decorations = False

    def clicked(self, index):
        model = self.ui.tree_view.model()

        column = index.column()
        if column == model.headers.indexes.reset:
            model.reset_node(index)
        elif column == model.headers.indexes.clear:
            model.clear_node(index)

    def _current_changed(self, new_index, old_index):
        model = self.ui.tree_view.model()
        new = model.node_from_index(new_index)

        selection_model = self.ui.tree_view.selectionModel()

        selection_model.clearSelection()
        nodes = set(new.frame.signals) & set(model.root.children)
        nodes.discard(new)
        for node in nodes:
            selection_model.select(
                model.index_from_node(node),
                QItemSelectionModel.Select | QItemSelectionModel.Rows
            )

    @pyqtSlot(str)
    def set_status_string(self, string):
        self.ui.status_label.setText(string)

    def context_menu(self, position):
        index = self.ui.tree_view.indexAt(position)

        if not index.isValid():
            return

        model = self.ui.tree_view.model()
        node = model.node_from_index(index)

        menu = QtWidgets.QMenu(parent=self.ui.tree_view)

        read = menu.addAction('Read {}'.format(
            self.ui.read_from_module_button.text()))
        write = menu.addAction('Write {}'.format(
            self.ui.write_to_module_button.text()))
        clear = menu.addAction('Clear Local')

        action = menu.exec(self.ui.tree_view.viewport().mapToGlobal(position))

        if action is None:
            pass
        elif action is read:
            model.root.read_all_from_device(only_these=(node,),
                                            callback=self.update_signals)
        elif action is write:
            model.root.write_all_to_device(only_these=(node,),
                                           callback=self.update_signals)
        elif action is clear:
            model.clear_node(index)

    def update_signals(self, d):
        model = self.ui.tree_view.model()

        for signal, value in d.items():
            # TODO: don't hardcode this here, some general 'ignore me' property
            if signal.name not in {'__padding__', 'ParameterResponse_MUX',
                                   'ParameterQuery_MUX', 'ReadParam_status'}:
                signal.set_signal.set_data(value)

        model.dataChanged.emit(QModelIndex(), QModelIndex())


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
