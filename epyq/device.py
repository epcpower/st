#!/usr/bin/env python3

# TODO: get some docstrings in here!

import can
import canmatrix.importany as importany
import epyq.canneo
import epyq.nv
import epyq.nvview
import epyq.overlaylabel
import epyq.txrx
import epyq.txrxview
import functools
import io
import json
import os
import shutil
import tempfile
import zipfile

from epyq.busproxy import BusProxy
from epyq.widgets.abstractwidget import AbstractWidget
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, Qt, QFile, QFileInfo, QTextStream, QObject

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def load(file):
    if isinstance(file, str):
        pass
    elif isinstance(file, io.IOBase):
        pass


class Device:
    def __init__(self, *args, **kwargs):
        if kwargs.get('file', None) is not None:
            constructor = self._init_from_file
        else:
            constructor = self._init_from_parameters

        constructor(*args, **kwargs)

    def __del__(self):
        self.bus.set_bus()

    def _init_from_file(self, file, bus=None, dash_only=False):
        try:
            zip_file = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            try:
                file = open(file, 'r')
            except TypeError:
                return
            else:
                self._load_config(file=file, bus=bus, dash_only=dash_only)
        else:
            self._init_from_zip(zip_file, bus=bus, dash_only=dash_only)

    def _load_config(self, file, bus=None, dash_only=False):
        s = file.read()
        d = json.loads(s)

        path = os.path.dirname(file.name)
        self.ui_path = os.path.join(path, d['ui_path'])
        self.can_path = os.path.join(path, d['can_path'])

        self.bus = BusProxy(bus=bus)

        self._init_from_parameters(
            ui=self.ui_path,
            serial_number=d.get('serial_number', ''),
            name=d.get('name', ''),
            dash_only=dash_only)

    def _init_from_zip(self, zip_file, bus=None, dash_only=False):
        path = tempfile.mkdtemp()
        zip_file.extractall(path=path)
        # TODO error dialog if no .epc found in zip file
        for f in os.listdir(path):
            if f.endswith(".epc"):
                file = os.path.join(path, f)
        with open(file, 'r') as file:
            self._load_config(file, bus=bus, dash_only=dash_only)

        shutil.rmtree(path)

    def _init_from_parameters(self, ui, serial_number, name, bus=None,
                              dash_only=False):
        if not hasattr(self, 'bus'):
            self.bus = BusProxy(bus=bus)

        self.serial_number = serial_number
        self.name = name

        device_ui = 'device.ui'
        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(device_ui).isAbsolute():
            ui_file = os.path.join(
                QFileInfo.absolutePath(QFileInfo(__file__)), device_ui)
        else:
            ui_file = device_ui
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly | QFile.Text)
        ts = QTextStream(ui_file)
        sio = io.StringIO(ts.readAll())
        self.ui = uic.loadUi(sio)

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
        self.dash_ui = uic.loadUi(sio)

        if dash_only:
            self.ui = self.dash_ui

            matrix = list(importany.importany(self.can_path).values())[0]
            self.neo_frames = epyq.canneo.Neo(matrix=matrix, bus=self.bus)

            notifiees = [self.neo_frames]
        else:
            self.ui.offline_overlay = epyq.overlaylabel.OverlayLabel(parent=self.ui)
            self.ui.offline_overlay.label.setText('offline')

            self.ui.dash_layout.addWidget(self.dash_ui)

            self.ui.name.setText(name)

            # TODO: the repetition here is not so pretty
            matrix_rx = list(importany.importany(self.can_path).values())[0]
            neo_rx = epyq.canneo.Neo(matrix=matrix_rx,
                                     frame_class=epyq.txrx.MessageNode,
                                     signal_class=epyq.txrx.SignalNode)

            matrix_tx = list(importany.importany(self.can_path).values())[0]
            message_node_tx_partial = functools.partial(epyq.txrx.MessageNode,
                                                        tx=True)
            signal_node_tx_partial = functools.partial(epyq.txrx.SignalNode,
                                                       tx=True)
            neo_tx = epyq.canneo.Neo(matrix=matrix_tx,
                                     frame_class=message_node_tx_partial,
                                     signal_class=signal_node_tx_partial)

            self.neo_frames = neo_tx
            notifiees = list(self.neo_frames.frames)

            rx = epyq.txrx.TxRx(tx=False, neo=neo_rx)
            notifiees.append(rx)
            rx_model = epyq.txrx.TxRxModel(rx)

            # TODO: put this all in the model...
            rx.changed.connect(rx_model.changed)
            rx.begin_insert_rows.connect(rx_model.begin_insert_rows)
            rx.end_insert_rows.connect(rx_model.end_insert_rows)

            tx = epyq.txrx.TxRx(tx=True, neo=neo_tx, bus=self.bus)
            tx_model = epyq.txrx.TxRxModel(tx)
            tx.changed.connect(tx_model.changed)

            txrx_views = self.ui.findChildren(epyq.txrxview.TxRxView)
            if len(txrx_views) > 0:
                # TODO: actually find them and actually support multiple
                self.ui.rx.setModel(rx_model)
                self.ui.tx.setModel(tx_model)


            matrix_nv = list(importany.importany(self.can_path).values())[0]
            self.frames_nv = epyq.canneo.Neo(matrix=matrix_nv,
                                             frame_class=epyq.nv.Frame,
                                             signal_class=epyq.nv.Nv)

            nv_views = self.ui.findChildren(epyq.nvview.NvView)
            if len(nv_views) > 0:
                try:
                    nvs = epyq.nv.Nvs(self.frames_nv, self.bus)
                except epyq.nv.NoNv:
                    pass
                else:
                    nv_model = epyq.nv.NvModel(nvs)
                    nvs.changed.connect(nv_model.changed)
                    notifiees.append(nvs)

                for view in nv_views:
                    view.setModel(nv_model)

        notifier = self.bus.notifier
        for notifiee in notifiees:
            notifier.add(notifiee)

        # TODO: CAMPid 99457281212789437474299
        children = self.ui.findChildren(QObject)
        widgets = [c for c in children if
                   isinstance(c, AbstractWidget)]

        self.connected_frames = []

        for widget in widgets:
            frame_name = widget.property('frame')
            signal_name = widget.property('signal')

            widget.set_label('{}:{}'.format(frame_name, signal_name))
            widget.set_range(min=0, max=100)
            widget.set_value(42)

            # TODO: add some notifications
            frame = self.neo_frames.frame_by_name(frame_name)
            if frame is not None:
                signal = frame.signal_by_name(signal_name)
                if signal is not None:
                    self.connected_frames.append(frame)
                    widget.set_signal(signal)
                    frame.user_send_control = False

    def get_frames(self):
        return self.frames

    @pyqtSlot(bool)
    def bus_status_changed(self, online):
        self.ui.offline_overlay.setVisible(not online)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
