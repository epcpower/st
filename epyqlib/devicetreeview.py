#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
import epyqlib.device
import epyqlib.devicetree
import epyqlib.flash
import functools
import io
import math
import os
import textwrap
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import (QApplication, QAction, QFileDialog, QHeaderView,
                             QMenu, QProgressDialog, QMessageBox)
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

    return epyqlib.device.Device(file=file, bus=bus)


class DeviceTreeView(QtWidgets.QWidget):
    device_selected = pyqtSignal(epyqlib.device.Device)

    def __init__(self, parent=None, in_designer=False):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

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

        self.resize_columns = epyqlib.devicetree.Columns(
            name=True,
            bitrate=False)

        self.ui.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_view.customContextMenuRequested.connect(
            self.context_menu
        )

        self.model = None

    def _current_changed(self, new_index, old_index):
        node = self.model.node_from_index(new_index)
        if isinstance(node, epyqlib.devicetree.Device):
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
        if isinstance(node, epyqlib.devicetree.Device):
            remove_device_action = menu.addAction('Close')
        if isinstance(node, epyqlib.devicetree.Bus):
            add_device_action = menu.addAction('Load device...')
            flash_action = menu.addAction('Flash...')
            flash_action.setEnabled(not node._checked.name
                                    and not node.fields.name == 'Offline')

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
        elif action is flash_action:
            self.flash(interface=node.interface,
                       channel=node.channel)

    def add_device(self, bus):
        device = load_device()
        if device is not None:
            device = epyqlib.devicetree.Device(device=device)

            self.model.add_device(bus, device)
            index = self.model.index_from_node(bus)
            index = self.model.index(index.row(), 0, index.parent())
            self.ui.tree_view.setExpanded(index, True)

        return device

    def flash(self, interface, channel):
        # TODO  CAMPid 9561616237195401795426778
        filters = [
            ('TICOFF Binaries', ['out']),
            ('All Files', ['*'])
        ]
        file = file_dialog(filters)

        if file is not None:
            message_box = QMessageBox(self)
            message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            message_box.setDefaultButton(QMessageBox.Cancel)
            message_box.setTextFormat(Qt.RichText)

            text = textwrap.dedent('''\
            Flashing {file}

            <ol>
              <li> Prepare module for programming
                <ul>
                  <li> Remove all high power from the module </li>
                  <li> Remove 24V control power </li>
                  <li> Install jumper between J1 pin 1 and pin 2 (+24V to Boot Enable), but do not reconnect 24V at this time </li>
                  <li> Ensure that the USB to CAN device is installed and connected to the appropriate CAN network </li>
                  <br>
                  <br>
                  <i> <b>Note:</b> no other devices may be active on the CAN network during programming operations </i>
                  <br>
                  <i> <b>Note:</b> firmware programming occurs at a CAN baud rate of 250kbits/sec.  If any CAN tools are in use during programming, they should be set to a baud rate of 250kbits/sec </i>
                </ul>
              </li>
              <br>
              <li> Apply firmware update via CAN
                <ul>
                  <li> Click OK </li>
                  <li> Reapply 24V control power </li>
                  <li> EPyQ will search for the module and should find it within a second or two </li>
                  <li> EPyQ will initiate clearing of module's flash memory </li>
                  <li> EPyQ will flash the device providing progress status </li>
                  <li> This whole process should take 1-2 minutes </li>
                </ul>
              </li>
              <br>
              <li> Restore System
                <ul>
                  <li> Remove 24V control power </li>
                  <li> Remove Boot Enable jumper </li>
                  <li> Power up module normally </li>
                </ul>
              </li>
            </ol>
            '''.format(file=file))

            message_box.setText(text)

            result = message_box.exec()

            if result == QMessageBox.Ok:
                with open(file, 'rb') as f:
                    real_bus = can.interface.Bus(bustype=interface,
                                                 channel=channel,
                                                 bitrate=250000)
                    bus = epyqlib.busproxy.BusProxy(bus=real_bus,
                                                    auto_disconnect=False)

                    progress = QProgressDialog(self)
                    flags =  progress.windowFlags()
                    flags &= ~Qt.WindowContextHelpButtonHint
                    progress.setWindowFlags(flags)
                    progress.setWindowModality(Qt.WindowModal)
                    progress.setAutoReset(False)

                    flasher = epyqlib.flash.Flasher(file=f,
                                                    bus=bus,
                                                    progress=progress,
                                                    retries=math.inf,
                                                    parent=self)

                    failed_box = QMessageBox(self)
                    failed_box.setText(textwrap.dedent('''\
                    Flashing failed
                    '''))

                    canceled_box = QMessageBox(self)
                    canceled_box.setText(textwrap.dedent('''\
                    Flashing canceled
                    '''))

                    flasher.done.connect(progress.close)
                    flasher.done.connect(bus.set_bus)

                    completed_format = textwrap.dedent('''\
                    Flashing completed successfully

                    Data time: {:.3f} seconds for {} bytes or {:.0f} bytes/second''')
                    flasher.completed.connect(
                        lambda f=flasher:
                            print(
                                completed_format.format(
                                    f.data_delta_time,
                                    f.download_bytes,
                                    f.download_bytes / f.data_delta_time
                                )
                            )
                    )
                    flasher.completed.connect(
                        lambda f=flasher:
                            QMessageBox.information(
                                self,
                                'EPyQ',
                                completed_format.format(
                                    f.data_delta_time,
                                    f.download_bytes,
                                    f.download_bytes / f.data_delta_time
                                )
                            )
                    )
                    flasher.failed.connect(failed_box.exec)
                    flasher.canceled.connect(canceled_box.exec)
                    flasher.done.connect(bus.set_bus)

                    flasher.flash()

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
            epyqlib.devicetree.Columns.indexes.bitrate,
            epyqlib.delegates.Combo(model=model, parent=self))

        self.ui.tree_view.selectionModel().currentChanged.connect(
            self._current_changed)

        widths = [self.ui.tree_view.columnWidth(i)
                  for i in epyqlib.devicetree.Columns.indexes]
        width = sum(widths)
        width += 2 * self.ui.tree_view.frameWidth()

        self.ui.tree_view.setMinimumWidth(1.25 * width)

        self.ui.tree_view.header().setSectionResizeMode(
            epyqlib.devicetree.Columns.indexes.name,
            QHeaderView.Stretch
        )


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
