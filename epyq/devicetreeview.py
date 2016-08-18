#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.device
import epyq.devicetree
import functools
import io
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QAction, QFileDialog, QHeaderView, QMenu
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QFile, QFileInfo,
                          QTextStream, QModelIndex, QItemSelectionModel)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def file_dialog(filters, default=0):
    # TODO: CAMPid 9857216134675885472598426718023132
    # filters = [
    #     ('EPC Packages', ['epc', 'epz']),
    #     ('All Files', ['*'])
    # ]
    # TODO: CAMPid 97456612391231265743713479129

    filter_strings = ['{} ({})'.format(f[0],
                                       ' '.join(['*.'+e for e in f[1]])
                                       ) for f in filters]
    filter_string = ';;'.join(filter_strings)

    file = QFileDialog.getOpenFileName(
            filter=filter_string,
            initialFilter=filter_strings[default])[0]

    if len(file) == 0:
        file = None

    return file


def load_device(bus=None, file=None):
    # TODO  CAMPid 9561616237195401795426778
    if file is None:
        filters = [
            ('EPC Packages', ['epc', 'epz']),
            ('All Files', ['*'])
        ]
        file = file_dialog(filters)

        if file is None:
            return

    return epyq.device.Device(file=file, bus=bus)


class DeviceTreeView(QtWidgets.QWidget):
    device_selected = pyqtSignal(epyq.device.Device)

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        ui = 'devicetreeview.ui'
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

        self.resize_columns = epyq.devicetree.Columns(
            name=True,
            bitrate=False)

        self.ui.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_view.customContextMenuRequested.connect(
            self.context_menu
        )

        self.model = None

    def _current_changed(self, new_index, old_index):
        node = self.model.node_from_index(new_index)
        if isinstance(node, epyq.devicetree.Device):
            device = node.device
            self.device_selected.emit(device)

    def context_menu(self, position):
        index = self.ui.tree_view.indexAt(position)

        if not index.isValid():
            return

        node = self.model.node_from_index(index)

        add_device_action = None
        remove_device_action = None

        menu = QMenu()
        if isinstance(node, epyq.devicetree.Device):
            remove_device_action = menu.addAction('Close')
        if isinstance(node, epyq.devicetree.Bus):
            add_device_action = menu.addAction('Load device...')

        action = menu.exec_(self.ui.tree_view.viewport().mapToGlobal(position))

        if action is None:
            pass
        elif action is remove_device_action:
            self.remove_device(node)
        elif action is add_device_action:
            device = self.add_device(node)
            if device is not None:
                self.ui.tree_view.selectionModel().setCurrentIndex(
                    self.model.index_from_node(device),
                    QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    def add_device(self, bus):
        device = load_device()
        if device is not None:
            device = epyq.devicetree.Device(device=device)

            self.model.add_device(bus, device)
            index = self.model.index_from_node(bus)
            index = self.model.index(index.row(), 0, index.parent())
            self.ui.tree_view.setExpanded(index, True)

        return device

    def remove_device(self, device):
        self.ui.tree_view.clearSelection()
        self.model.remove_device(device)

    def setModel(self, model):
        self.model = model
        self.ui.tree_view.setModel(model)

        self.ui.tree_view.header().setStretchLastSection(False)

        for i, resize in enumerate(self.resize_columns):
            if resize:
                self.ui.tree_view.header().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeToContents)

        self.ui.tree_view.setItemDelegateForColumn(
            epyq.devicetree.Columns.indexes.bitrate,
            epyq.delegates.Combo(model=model, parent=self))

        self.ui.tree_view.selectionModel().currentChanged.connect(
            self._current_changed)

        widths = [self.ui.tree_view.columnWidth(i)
                  for i in epyq.devicetree.Columns.indexes]
        width = sum(widths)
        width += 2 * self.ui.tree_view.frameWidth()

        self.ui.tree_view.setMinimumWidth(1.25 * width)

        self.ui.tree_view.header().setSectionResizeMode(
            epyq.devicetree.Columns.indexes.name,
            QHeaderView.Stretch
        )


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
