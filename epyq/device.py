#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import can
import canmatrix.importany as importany
import epyq.canneo
import epyq.nv
import epyq.nvview
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
from PyQt5.QtCore import QFile, QFileInfo, QTextStream, QObject

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

    def _init_from_file(self, file, bus=None):
        try:
            zip_file = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            try:
                file = open(file, 'r')
            except TypeError:
                return
            else:
                self._load_config(file=file, bus=bus)
        else:
            self._init_from_zip(zip_file, bus=bus)

    def _load_config(self, file, bus=None):
        s = file.read()
        d = json.loads(s)

        path = os.path.dirname(file.name)
        self.ui_path = os.path.join(path, d['ui_path'])
        self.can_path = os.path.join(path, d['can_path'])

        matrix = list(importany.importany(self.can_path).values())[0]
        self.frames = epyq.canneo.neotize(matrix=matrix)

        self._init_from_parameters(
            matrix=matrix,
            ui=self.ui_path,
            serial_number=d.get('serial_number', ''),
            name=d.get('name', ''),
            bus=bus)

    def _init_from_zip(self, zip_file, bus=None):
        path = tempfile.mkdtemp()
        zip_file.extractall(path=path)

        file = os.path.join(path, 'config.epc')
        with open(file, 'r') as file:
            self._load_config(file, bus=bus)

        shutil.rmtree(path)

    def _init_from_parameters(self, matrix, ui, serial_number, name, bus=None):
        self.bus = BusProxy(bus=bus)

        self.matrix = matrix
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

        self.ui.dash_layout.addWidget(self.dash_ui)

        self.dash_ui.name.setText(name)

        notifiees = self.frames

        # TODO: the repetition here is not so pretty
        matrix_rx = list(importany.importany(self.can_path).values())[0]
        epyq.canneo.neotize(matrix=matrix_rx,
                            frame_class=epyq.txrx.MessageNode,
                            signal_class=epyq.txrx.SignalNode)

        matrix_tx = list(importany.importany(self.can_path).values())[0]
        message_node_tx_partial = functools.partial(epyq.txrx.MessageNode,
                                                    tx=True)
        signal_node_tx_partial = functools.partial(epyq.txrx.SignalNode,
                                                   tx=True)
        epyq.canneo.neotize(matrix=matrix_tx,
                            frame_class=message_node_tx_partial,
                            signal_class=signal_node_tx_partial)

        rx = epyq.txrx.TxRx(tx=False, matrix=matrix_rx)
        notifiees.append(rx)
        rx_model = epyq.txrx.TxRxModel(rx)

        # TODO: put this all in the model...
        rx.changed.connect(rx_model.changed)
        rx.begin_insert_rows.connect(rx_model.begin_insert_rows)
        rx.end_insert_rows.connect(rx_model.end_insert_rows)

        tx = epyq.txrx.TxRx(tx=True, matrix=matrix_tx, bus=bus)
        tx_model = epyq.txrx.TxRxModel(tx)

        txrx_views = self.ui.findChildren(epyq.txrxview.TxRxView)
        if len(txrx_views) > 0:
            # TODO: actually find them and actually support multiple
            self.ui.rx.setModel(rx_model)
            self.ui.tx.setModel(tx_model)


        matrix_nv = list(importany.importany(self.can_path).values())[0]
        self.frames_nv = epyq.canneo.neotize(matrix=matrix_nv)
        epyq.canneo.neotize(
                matrix=matrix_nv,
                frame_class=epyq.nv.Frame,
                signal_class=epyq.nv.Nv)

        nv_views = self.ui.findChildren(epyq.nvview.NvView)
        if len(nv_views) > 0:
            try:
                nvs = epyq.nv.Nvs(matrix_nv, bus)
            except epyq.nv.NoNv:
                pass
            else:
                nv_model = epyq.nv.NvModel(nvs)
                nvs.changed.connect(nv_model.changed)
                notifiees.append(nvs)

            for view in nv_views:
                view.setModel(nv_model)

        self.notifier = can.Notifier(self.bus, notifiees, timeout=0.1)

        # TODO: CAMPid 99457281212789437474299
        children = self.ui.findChildren(QObject)
        widgets = [c for c in children if
                   isinstance(c, AbstractWidget)]

        for widget in widgets:
            frame_name = widget.property('frame')
            signal_name = widget.property('signal')

            widget.set_label('{}:{}'.format(frame_name, signal_name))
            widget.set_range(min=0, max=100)
            widget.set_value(42)

            # TODO: add some notifications
            frame = matrix.frameByName(frame_name)
            if frame is not None:
                frame = frame.frame
                signal = frame.frame.signalByName(signal_name)
                if signal is not None:
                    widget.set_signal(signal.signal)

    def get_frames(self):
        return self.frames


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
