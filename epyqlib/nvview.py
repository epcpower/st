#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.nv
import epyqlib.utils.qt
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
            comment=True,
        )

        self.ui.tree_view.clicked.connect(self.clicked)
        self.ui.tree_view.header().setMinimumSectionSize(0)

        self.progress = None

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
        only_these = [nv for nv in model.all_nv()
                      if nv.value is not None]
        callback = functools.partial(
            self.update_signals,
            only_these=only_these
        )
        model.root.write_all_to_device(callback=callback,
                                       only_these=only_these)

    def read_from_module(self):
        model = self.nonproxy_model()
        only_these = [nv for nv in model.all_nv()]
        callback = functools.partial(
            self.update_signals,
            only_these=only_these
        )
        model.root.read_all_from_device(callback=callback,
                                        only_these=only_these)

    def setModel(self, model):
        proxy = model
        proxy.setSortRole(epyqlib.pyqabstractitemmodel.UserRoles.sort)
        self.ui.tree_view.setModel(proxy)

        model = self.nonproxy_model()
        model.activity_started.connect(self.activity_started)
        model.activity_ended.connect(self.activity_ended)

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

        for i in epyqlib.nv.Columns.indexes:
            if self.resize_columns[i]:
                self.ui.tree_view.header().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)

        self.ui.tree_view.setItemDelegateForColumn(
            epyqlib.nv.Columns.indexes.value,
            epyqlib.delegates.ByFunction(model=model, proxy=proxy, parent=self)
        )

        self.ui.tree_view.setColumnHidden(
            epyqlib.nv.Columns.indexes.factory,
            not any(nv.is_factory() for nv in model.root.all_nv())
        )

        model.force_action_decorations = True
        for column in model.icon_columns:
            self.ui.tree_view.resizeColumnToContents(column)
            self.ui.tree_view.header().setSectionResizeMode(
                column, QtWidgets.QHeaderView.Fixed)

        max_icon_column_width = max(
            self.ui.tree_view.columnWidth(c) for c in model.icon_columns
        )

        for column in model.icon_columns:
            self.ui.tree_view.header().setMinimumSectionSize(0)
            self.ui.tree_view.setColumnWidth(column, max_icon_column_width)

        model.force_action_decorations = False

    def clicked(self, index):
        model = self.nonproxy_model()
        index = self.ui.tree_view.model().mapToSource(index)
        node = model.node_from_index(index)

        if isinstance(node, epyqlib.nv.Nv):
            column = index.column()
            if column == model.headers.indexes.saturate:
                model.saturate_node(node)
            elif column == model.headers.indexes.reset:
                model.reset_node(node)
            elif column == model.headers.indexes.clear:
                model.clear_node(node)

    @pyqtSlot(str)
    def activity_started(self, string):
        self.ui.status_label.setText(string)
        self.progress = epyqlib.utils.qt.Progress()
        self.progress.connect(
            progress=epyqlib.utils.qt.progress_dialog(parent=self),
            label_text=string,
        )

    @pyqtSlot(str)
    def activity_ended(self, string):
        self.ui.status_label.setText(string)
        if self.progress is not None:
            self.progress.complete()
            self.progress = None

    def context_menu(self, position):
        proxy = self.ui.tree_view.model()

        index = self.ui.tree_view.indexAt(position)
        index = proxy.mapToSource(index)

        model = self.nonproxy_model()

        node = model.node_from_index(index)
        node_type = type(node)

        dispatch = {
            epyqlib.nv.Nv: self.nv_context_menu
        }

        f = dispatch.get(node_type)
        if f is not None:
            f(position)

    def nv_context_menu(self, position):
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
        selected_nodes = tuple(
            node for node in selected_nodes if isinstance(node, epyqlib.nv.Nv)
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

        for signal in frame.set_frame.parameter_signals:
            model.dynamic_columns_changed(signal)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
