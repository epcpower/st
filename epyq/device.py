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

from collections import OrderedDict
from epyq.busproxy import BusProxy
from epyq.widgets.abstractwidget import AbstractWidget
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, Qt, QFile, QFileInfo, QTextStream, QObject

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def j1939_node_id_adjust(message_id, node_id):
    if node_id == 0:
        return

    raise Exception('J1939 node id adjustment not yet implemented')


def transpower_node_id_adjust(message_id, node_id):
    return message_id + node_id


node_id_types = OrderedDict([
    ('j1939', j1939_node_id_adjust),
    ('simple', transpower_node_id_adjust)
])


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

    def _init_from_file(self, file, bus=None):
        try:
            zip_file = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            try:
                self.config_path = os.path.abspath(file)
                file = open(file, 'r')
            except TypeError:
                return
            else:
                self._load_config(file=file, bus=bus)
        else:
            self._init_from_zip(zip_file, bus=bus)

    def _load_config(self, file, bus=None):
        s = file.read()
        d = json.loads(s, object_pairs_hook=OrderedDict)

        path = os.path.dirname(file.name)
        for ui_path_name in ['ui_path', 'ui_paths']:
            try:
                json_ui_paths = d[ui_path_name]
                break
            except KeyError:
                pass

        self.ui_paths = OrderedDict()
        try:
            for name, ui_path in json_ui_paths.items():
                self.ui_paths[name] = ui_path
        except AttributeError:
            self.ui_paths["Dash"] = json_ui_paths

        self.can_path = os.path.join(path, d['can_path'])

        self.bus = BusProxy(bus=bus)
        self.node_id_type = d.get('node_id_type',
                                  next(iter(node_id_types))).lower()
        self.node_id = int(d.get('node_id', 0))
        self.node_id_adjust = functools.partial(
            node_id_types[self.node_id_type],
            node_id=self.node_id
        )

        self._init_from_parameters(
            uis=self.ui_paths,
            serial_number=d.get('serial_number', ''),
            name=d.get('name', ''))

    def _init_from_zip(self, zip_file, bus=None):
        path = tempfile.mkdtemp()
        zip_file.extractall(path=path)
        # TODO error dialog if no .epc found in zip file
        for f in os.listdir(path):
            if f.endswith(".epc"):
                file = os.path.join(path, f)
        self.config_path = os.path.abspath(file)
        with open(file, 'r') as file:
            self._load_config(file, bus=bus)

        shutil.rmtree(path)

    def _init_from_parameters(self, uis, serial_number, name, bus=None):
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

        self.ui.offline_overlay = epyq.overlaylabel.OverlayLabel(parent=self.ui)
        self.ui.offline_overlay.label.setText('offline')

        self.ui.name.setText(self.name)

        self.dash_uis = {}
        for i, (name, path) in enumerate(uis.items()):
            # TODO: CAMPid 9549757292917394095482739548437597676742
            if not QFileInfo(path).isAbsolute():
                ui_file = os.path.join(
                    QFileInfo.absolutePath(QFileInfo(self.config_path)), path)
            else:
                ui_file = path
            ui_file = QFile(ui_file)
            ui_file.open(QFile.ReadOnly | QFile.Text)
            ts = QTextStream(ui_file)
            sio = io.StringIO(ts.readAll())
            self.dash_uis[name] = uic.loadUi(sio)

            self.ui.tabs.insertTab(i,
                                   self.dash_uis[name],
                                   name)

        self.ui.tabs.setCurrentIndex(0)

        # TODO: the repetition here is not so pretty
        matrix_rx = list(importany.importany(self.can_path).values())[0]
        neo_rx = epyq.canneo.Neo(matrix=matrix_rx,
                                 frame_class=epyq.txrx.MessageNode,
                                 signal_class=epyq.txrx.SignalNode,
                                 node_id_adjust=self.node_id_adjust)

        matrix_tx = list(importany.importany(self.can_path).values())[0]
        message_node_tx_partial = functools.partial(epyq.txrx.MessageNode,
                                                    tx=True)
        signal_node_tx_partial = functools.partial(epyq.txrx.SignalNode,
                                                   tx=True)
        neo_tx = epyq.canneo.Neo(matrix=matrix_tx,
                                 frame_class=message_node_tx_partial,
                                 signal_class=signal_node_tx_partial,
                                 node_id_adjust=self.node_id_adjust)

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
        self.frames_nv = epyq.canneo.Neo(
            matrix=matrix_nv,
            frame_class=epyq.nv.Frame,
            signal_class=epyq.nv.Nv,
            node_id_adjust=self.node_id_adjust
        )

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

        for widget in widgets:
            frame_name = widget.property('frame')
            signal_name = widget.property('signal')

            widget.set_range(min=0, max=100)
            widget.set_value(42)

            # TODO: add some notifications
            frame = self.neo_frames.frame_by_name(frame_name)
            if frame is not None:
                signal = frame.signal_by_name(signal_name)
                if signal is not None:
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
