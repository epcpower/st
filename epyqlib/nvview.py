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
                          QModelIndex, QSortFilterProxyModel)

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

        view = self.ui.tree_view
        view.setContextMenuPolicy(Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(self.context_menu)
        view.setSelectionBehavior(view.SelectRows)
        view.setSelectionMode(view.ExtendedSelection)

        self.resize_columns = epyqlib.nv.Columns(
            name=True,
            value=True,
            min=True,
            max=True,
            factory=True,
            comment=True,
        )

        self.ui.tree_view.clicked.connect(self.clicked)

    # TODO: CAMPid 07943342700734207878034207087
    def nonproxy_model(self):
        model = self.ui.tree_view.model()
        while isinstance(model, QSortFilterProxyModel):
            model = model.sourceModel()

        return model

    def set_sorting_enabled(self, enabled):
        self.ui.tree_view.setSortingEnabled(enabled)

    def sort_by_column(self, column, order):
        self.ui.tree_view.sortByColumn(column, order)

    def write_to_module(self):
        model = self.nonproxy_model()
        only_these = [nv for nv in model.root.children
                      if nv.value is not None]
        model.root.write_all_to_device(callback=self.update_signals,
                                       only_these = only_these)

    def read_from_module(self):
        model = self.nonproxy_model()
        model.root.read_all_from_device(callback=self.update_signals)

    def setModel(self, model):
        proxy = model
        self.ui.tree_view.setModel(proxy)

        model = self.nonproxy_model()
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
            epyqlib.delegates.ByFunction(model=model, proxy=proxy, parent=self)
        )

        self.ui.tree_view.setColumnHidden(
            epyqlib.nv.Columns.indexes.factory,
            all(len(nv.fields.factory) == 0 for nv in model.root.children)
        )

        model.force_action_decorations = True
        decoration_only_columns = (
            model.headers.indexes.saturate,
            model.headers.indexes.clear,
            model.headers.indexes.reset,
        )
        for column in decoration_only_columns:
            self.ui.tree_view.resizeColumnToContents(column)
            self.ui.tree_view.header().setSectionResizeMode(
                column, QtWidgets.QHeaderView.Fixed)
        model.force_action_decorations = False

    def clicked(self, index):
        model = self.nonproxy_model()
        index = self.ui.tree_view.model().mapToSource(index)
        node = model.node_from_index(index)

        column = index.column()
        if column == model.headers.indexes.saturate:
            model.saturate_node(node)
        elif column == model.headers.indexes.reset:
            model.reset_node(node)
        elif column == model.headers.indexes.clear:
            model.clear_node(node)

    @pyqtSlot(str)
    def set_status_string(self, string):
        self.ui.status_label.setText(string)

    def context_menu(self, position):
        proxy = self.ui.tree_view.model()

        model = self.nonproxy_model()
        selection_model = self.ui.tree_view.selectionModel()
        selected_indexes = selection_model.selectedRows()
        selected_indexes = tuple(
            proxy.mapToSource(i) for i in selected_indexes
        )
        selected_nodes = tuple(
            model.node_from_index(i) for i in selected_indexes
        )

        menu = QtWidgets.QMenu(parent=self.ui.tree_view)

        read = menu.addAction('Read {}'.format(
            self.ui.read_from_module_button.text()))
        write = menu.addAction('Write {}'.format(
            self.ui.write_to_module_button.text()))
        saturate = menu.addAction('Saturate')
        if not any(n.can_be_saturated() for n in selected_nodes):
            saturate.setDisabled(True)
        reset = menu.addAction('Reset')
        if not any(n.can_be_reset() for n in selected_nodes):
            reset.setDisabled(True)
        clear = menu.addAction('Clear')
        if not any(n.can_be_cleared() for n in selected_nodes):
            clear.setDisabled(True)

        action = menu.exec(self.ui.tree_view.viewport().mapToGlobal(position))

        callback = functools.partial(
            self.update_signals,
            only_these=selected_nodes
        )
        if action is None:
            pass
        elif action is read:
            model.root.read_all_from_device(only_these=selected_nodes,
                                            callback=callback)
        elif action is write:
            model.root.write_all_to_device(only_these=selected_nodes,
                                           callback=callback)
        elif action is saturate:
            for node in selected_nodes:
                model.saturate_node(node)
        elif action is reset:
            for node in selected_nodes:
                model.reset_node(node)
        elif action is clear:
            for node in selected_nodes:
                model.clear_node(node)

    def update_signals(self, d, only_these):
        model = self.nonproxy_model()

        frame = next(iter(d)).frame

        signals = set(only_these) & set(frame.set_frame.parameter_signals)

        for signal in signals:
            if signal.status_signal in d:
                value = d[signal.status_signal]
                signal.set_data(value, check_range=False)
            for column in range(signal.fields.indexes.saturate,
                                signal.fields.indexes.clear + 1):
                model.changed(signal, column,
                              signal, column,
                              (Qt.DisplayRole,))


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
