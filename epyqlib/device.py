#!/usr/bin/env python3

# TODO: get some docstrings in here!

import logging
logger = logging.getLogger(__name__)

import attr
import can
import canmatrix.formats
import epyqlib.canneo
import epyqlib.deviceextension
try:
    import epyqlib.resources.code
except ImportError:
    pass # we will catch the failure to open the file
import epyqlib.nv
import epyqlib.nvview
import epyqlib.overlaylabel
import epyqlib.twisted.loopingset
import epyqlib.txrx
import epyqlib.txrxview
import epyqlib.utils.qt
import epyqlib.variableselectionmodel
import functools
import importlib.util
import io
import itertools
import json
import math
import os
import shutil
import tempfile
import textwrap
import twisted.internet.task
import zipfile
from twisted.internet.defer import setDebugging
setDebugging(True)

from collections import OrderedDict
from enum import Enum, unique
from epyqlib.busproxy import BusProxy
from epyqlib.widgets.abstractwidget import AbstractWidget
from PyQt5 import uic
from PyQt5.QtCore import (pyqtSlot, Qt, QFile, QFileInfo, QTextStream, QObject,
                          QSortFilterProxyModel, QIODevice)
from PyQt5.QtWidgets import QWidget, QMessageBox, QInputDialog, QLineEdit

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CancelError(Exception):
    pass


@unique
class Elements(Enum):
    dash = 1
    tx = 2
    rx = 3
    variables = 4
    nv = 5


@unique
class Tabs(Enum):
    dashes = 1
    txrx = 2
    variables = 3
    nv = 4

    @classmethod
    def defaults(cls):
        return set(cls) - set((cls.variables,))


def j1939_node_id_adjust(message_id, node_id):
    if node_id == 0:
        return message_id

    raise Exception('J1939 node id adjustment not yet implemented')


def simple_node_id_adjust(message_id, node_id):
    return message_id + node_id


node_id_types = OrderedDict([
    ('j1939', j1939_node_id_adjust),
    ('simple', simple_node_id_adjust)
])


@attr.s
class CanConfiguration:
    data_logger_reset_signal_path = attr.ib()
    data_logger_recording_signal_path = attr.ib()
    data_logger_configuration_is_valid_signal_path = attr.ib()


can_configurations = {
    'original': CanConfiguration(
        data_logger_reset_signal_path=(
            'CommandModeControl', 'ResetDatalogger'),
        data_logger_recording_signal_path=(
            'StatusBits', 'DataloggerRecording'),
        data_logger_configuration_is_valid_signal_path=(
            'StatusBits', 'DataloggerConfigurationIsValid')
    ),
    'j1939': CanConfiguration(
        data_logger_reset_signal_path=(
            'ParameterQuery', 'DataloggerConfig', 'ResetDatalogger'),
        data_logger_recording_signal_path=(
            'ParameterQuery', 'DataloggerStatus', 'DataloggerRecording'),
        data_logger_configuration_is_valid_signal_path=(
            'ParameterQuery', 'DataloggerStatus',
            'DataloggerConfigurationIsValid')
    )
}


def load(file):
    if isinstance(file, str):
        pass
    elif isinstance(file, io.IOBase):
        pass


class Device:
    def __init__(self, *args, **kwargs):
        self.bus = None
        self.from_zip = False

        if kwargs.get('file', None) is not None:
            constructor = self._init_from_file
        else:
            constructor = self._init_from_parameters

        constructor(*args, **kwargs)

    def __del__(self):
        if self.bus is not None:
            self.bus.set_bus()

    def _init_from_file(self, file, only_for_files=False, **kwargs):
        try:
            zip_file = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            try:
                self.config_path = os.path.abspath(file)
                file = open(file, 'r')
            except TypeError:
                return
            else:
                self._load_config(file=file, only_for_files=only_for_files,
                                  **kwargs)
        else:
            self._init_from_zip(zip_file, **kwargs)

    def _load_config(self, file, elements=None,
                     tabs=None, rx_interval=0, edit_actions=None,
                     only_for_files=False, **kwargs):
        if tabs is None:
            tabs = Tabs.defaults()

        self.elements = Elements if elements == None else elements
        self.elements = set(Elements)

        s = file.read()
        d = json.loads(s, object_pairs_hook=OrderedDict)
        self.raw_dict = d

        self.module_path = d.get('module', None)
        self.plugin = None
        if self.module_path is None:
            extension_class = epyqlib.deviceextension.DeviceExtension
        else:
            spec = importlib.util.spec_from_file_location(
                'extension', self.absolute_path(self.module_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            extension_class = module.DeviceExtension

        import weakref
        self.extension = extension_class(device=weakref.ref(self))

        path = os.path.dirname(file.name)
        for ui_path_name in ['ui_path', 'ui_paths', 'menu']:
            try:
                json_ui_paths = d[ui_path_name]
                break
            except KeyError:
                pass
        else:
            json_ui_paths = {}

        if not isinstance(json_ui_paths, dict):
            json_ui_paths = {"Dash": json_ui_paths}

        self.ui_paths = json_ui_paths

        for tab in Tabs:
            try:
                value = d['tabs'][tab.name]
            except KeyError:
                pass
            else:
                if int(value):
                    tabs.add(tab)
                else:
                    tabs.discard(tab)

        if Tabs.txrx not in tabs:
            self.elements.discard(Elements.tx)
            self.elements.discard(Elements.rx)

        if Tabs.variables not in tabs:
            self.elements.discard(Elements.variables)

        if Tabs.nv not in tabs:
            self.elements.discard(Elements.nv)

        self.can_path = os.path.join(path, d['can_path'])

        self.node_id_type = d.get('node_id_type',
                                  next(iter(node_id_types))).lower()
        self.node_id = int(d.get('node_id', 0))
        self.node_id_adjust = functools.partial(
            node_id_types[self.node_id_type],
            node_id=self.node_id
        )

        self.referenced_files = [
            f for f in [
                d.get('module', None),
                d.get('can_path', None),
                d.get('compatibility', None),
                d.get('parameter_defaults', None),
                *self.ui_paths.values()
            ]
            if f is not None
        ]

        self.shas = []
        compatibility_file = d.get('compatibility', None)
        if compatibility_file is not None:
            compatibility_file = os.path.join(
                os.path.dirname(self.config_path), compatibility_file)
            with open(compatibility_file) as file:
                s = file.read()
                c = json.loads(s, object_pairs_hook=OrderedDict)

            self.shas.extend(c.get('shas', []))

        if not only_for_files:
            self._init_from_parameters(
                uis=self.ui_paths,
                serial_number=d.get('serial_number', ''),
                name=d.get('name', ''),
                tabs=tabs,
                rx_interval=rx_interval,
                edit_actions=edit_actions,
                nv_configuration=d.get('nv_configuration'),
                can_configuration=d.get('can_configuration'),
                **kwargs)

    def _init_from_zip(self, zip_file, rx_interval=0, **kwargs):
        self.from_zip = True
        path = tempfile.mkdtemp()

        code = epyqlib.utils.qt.get_code()

        while True:
            try:
                zip_file.extractall(path=path, pwd=code)
            except RuntimeError:
                code, ok = QInputDialog.getText(
                    None,
                    '.epz Password',
                    '.epz Password',
                    QLineEdit.Password)

                if not ok:
                    raise CancelError('User canceled password dialog')

                code = code.encode('ascii')
            else:
                break

        # TODO error dialog if no .epc found in zip file
        for f in os.listdir(path):
            if f.endswith(".epc"):
                file = os.path.join(path, f)
        self.config_path = os.path.abspath(file)
        with open(file, 'r') as file:
            self._load_config(file, rx_interval=rx_interval, **kwargs)

        shutil.rmtree(path)

    def _init_from_parameters(self, uis, serial_number, name, bus=None,
                              tabs=None, rx_interval=0, edit_actions=None,
                              nv_configuration=None, can_configuration=None):
        if tabs is None:
            tabs = Tabs.defaults()

        if can_configuration is None:
            can_configuration = 'original'

        can_configuration = can_configurations[can_configuration]

        self.bus = BusProxy(bus=bus)

        self.rx_interval = rx_interval
        self.serial_number = serial_number
        self.name = '{name} :{id}'.format(name=name,
                                          id=self.node_id)

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
        self.loaded_uis = {}

        def traverse(dict_node):
            for key, value in dict_node.items():
                if isinstance(value, dict):
                    traverse(value)
                elif value.endswith('.ui'):
                    path = value
                    try:
                        dict_node[key] = self.loaded_uis[path]
                    except KeyError:
                        # TODO: CAMPid 9549757292917394095482739548437597676742
                        if not QFileInfo(path).isAbsolute():
                            ui_file = os.path.join(
                                QFileInfo.absolutePath(QFileInfo(self.config_path)),
                                path)
                        else:
                            ui_file = path
                        ui_file = QFile(ui_file)
                        ui_file.open(QFile.ReadOnly | QFile.Text)
                        ts = QTextStream(ui_file)
                        sio = io.StringIO(ts.readAll())
                        dict_node[key] = uic.loadUi(sio)
                        dict_node[key].file_name = path
                        self.loaded_uis[path] = dict_node[key]

        traverse(uis)

        # TODO: yuck, actually tidy the code
        self.dash_uis = uis

        notifiees = []

        if Elements.dash in self.elements:
            self.uis = self.dash_uis

            matrix = list(canmatrix.formats.loadp(self.can_path).values())[0]
            # TODO: this is icky
            if Elements.tx not in self.elements:
                self.neo_frames = epyqlib.canneo.Neo(matrix=matrix,
                                                  bus=self.bus,
                                                  rx_interval=self.rx_interval)

                notifiees.append(self.neo_frames)

        if Elements.rx in self.elements:
            # TODO: the repetition here is not so pretty
            matrix_rx = list(canmatrix.formats.loadp(self.can_path).values())[0]
            neo_rx = epyqlib.canneo.Neo(matrix=matrix_rx,
                                     frame_class=epyqlib.txrx.MessageNode,
                                     signal_class=epyqlib.txrx.SignalNode,
                                     node_id_adjust=self.node_id_adjust)

            rx = epyqlib.txrx.TxRx(tx=False, neo=neo_rx)
            notifiees.append(rx)
            rx_model = epyqlib.txrx.TxRxModel(rx)

            # TODO: put this all in the model...
            rx.changed.connect(rx_model.changed)
            rx.begin_insert_rows.connect(rx_model.begin_insert_rows)
            rx.end_insert_rows.connect(rx_model.end_insert_rows)

        if Elements.tx in self.elements:
            matrix_tx = list(canmatrix.formats.loadp(self.can_path).values())[0]
            message_node_tx_partial = functools.partial(epyqlib.txrx.MessageNode,
                                                        tx=True)
            signal_node_tx_partial = functools.partial(epyqlib.txrx.SignalNode,
                                                       tx=True)
            neo_tx = epyqlib.canneo.Neo(matrix=matrix_tx,
                                     frame_class=message_node_tx_partial,
                                     signal_class=signal_node_tx_partial,
                                     node_id_adjust=self.node_id_adjust)
            notifiees.extend(f for f in neo_tx.frames if f.mux_name is None)

            self.neo_frames = neo_tx

            tx = epyqlib.txrx.TxRx(tx=True, neo=neo_tx, bus=self.bus)
            tx_model = epyqlib.txrx.TxRxModel(tx)
            tx.changed.connect(tx_model.changed)

        # TODO: something with sets instead?
        if (Elements.rx in self.elements or
            Elements.tx in self.elements):
            txrx_views = self.ui.findChildren(epyqlib.txrxview.TxRxView)
            if len(txrx_views) > 0:
                # TODO: actually find them and actually support multiple
                self.ui.rx.setModel(rx_model)
                self.ui.tx.setModel(tx_model)

        if Elements.nv in self.elements:
            matrix_nv = list(canmatrix.formats.loadp(self.can_path).values())[0]
            self.frames_nv = epyqlib.canneo.Neo(
                matrix=matrix_nv,
                frame_class=epyqlib.nv.Frame,
                signal_class=epyqlib.nv.Nv,
                node_id_adjust=self.node_id_adjust
            )

            self.nv_looping_set = epyqlib.twisted.loopingset.Set()

            self.nvs = epyqlib.nv.Nvs(
                neo=self.frames_nv,
                bus=self.bus,
                configuration=nv_configuration
            )

            if 'parameter_defaults' in self.raw_dict:
                parameter_defaults_path = os.path.join(
                    os.path.dirname(self.config_path),
                    self.raw_dict['parameter_defaults']
                )
                with open(parameter_defaults_path) as f:
                    self.nvs.defaults_from_dict(json.load(f))
                    for nv in self.nvs.children:
                        nv.fields.default = nv.format_strings(
                            value=int(nv.default_value))[0]

            self.widget_frames_nv = epyqlib.canneo.Neo(
                matrix=matrix_nv,
                frame_class=epyqlib.nv.Frame,
                signal_class=epyqlib.nv.Nv,
                node_id_adjust=self.node_id_adjust
            )
            self.widget_nvs = epyqlib.nv.Nvs(
                neo=self.widget_frames_nv,
                bus=self.bus,
                stop_cyclic=self.nv_looping_set.stop,
                start_cyclic=self.nv_looping_set.start,
                configuration=nv_configuration
            )
            notifiees.append(self.widget_nvs)

            nv_views = self.ui.findChildren(epyqlib.nvview.NvView)
            if len(nv_views) > 0:
                nv_model = epyqlib.nv.NvModel(self.nvs)
                self.nvs.changed.connect(nv_model.changed)

                for view in nv_views:
                    view.setModel(nv_model)

        if Elements.variables in self.elements:
            variable_model = epyqlib.variableselectionmodel.VariableModel(
                nvs=self.nvs,
                bus=self.bus,
                tx_id=self.neo_frames.frame_by_name('CCP').id,
                rx_id=self.neo_frames.frame_by_name('CCPResponse').id
            )

            proxy = QSortFilterProxyModel()
            proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
            proxy.setSourceModel(variable_model)
            self.ui.variable_selection.set_model(proxy)
            self.ui.variable_selection.set_sorting_enabled(True)
            self.ui.variable_selection.sort_by_column(
                column=epyqlib.variableselectionmodel.Columns.indexes.name,
                order=Qt.AscendingOrder
            )
            self.ui.variable_selection.set_signal_paths(
                reset_signal_path=
                    can_configuration.data_logger_reset_signal_path,
                recording_signal_path=
                    can_configuration.data_logger_recording_signal_path,
                configuration_is_valid_signal_path=
                    can_configuration.data_logger_configuration_is_valid_signal_path,
            )

        if Tabs.dashes in tabs:
            for i, (name, dash) in enumerate(self.dash_uis.items()):
                self.ui.tabs.insertTab(i,
                                       dash,
                                       name)
        if Tabs.txrx not in tabs:
            self.ui.tabs.removeTab(self.ui.tabs.indexOf(self.ui.txrx))
        if Tabs.variables not in tabs:
            self.ui.tabs.removeTab(self.ui.tabs.indexOf(self.ui.variables))
        if Tabs.nv not in tabs:
            self.ui.tabs.removeTab(self.ui.tabs.indexOf(self.ui.nv))
        else:
            def tab_changed(index):
                if index == self.ui.tabs.indexOf(self.ui.nv):
                    self.nv_looping_set.stop()
                else:
                    self.nv_looping_set.start()

            self.ui.tabs.currentChanged.connect(tab_changed)

        self.ui.offline_overlay = epyqlib.overlaylabel.OverlayLabel(parent=self.ui)
        self.ui.offline_overlay.label.setText('offline')

        self.ui.name.setText(self.name)
        self.ui.tabs.setCurrentIndex(0)



        notifier = self.bus.notifier
        for notifiee in notifiees:
            notifier.add(notifiee)

        def flatten(dict_node):
            flat = set()
            for key, value in dict_node.items():
                if isinstance(value, dict):
                    flat |= flatten(value)
                else:
                    flat.add(value)

            return flat

        flat = flatten(self.dash_uis)
        flat = [v for v in flat if isinstance(v, QWidget)]

        default_widget_value = math.nan

        self.dash_connected_signals = set()
        self.dash_missing_signals = set()
        self.dash_missing_defaults = set()
        self.nv_looping_reads = {}
        if Tabs.variables in tabs:
            flat.append(self.ui.variable_selection)
        for dash in flat:
            # TODO: CAMPid 99457281212789437474299
            children = dash.findChildren(QObject)
            widgets = [c for c in children if
                       isinstance(c, AbstractWidget)]

            dash.connected_frames = set()
            frames = dash.connected_frames

            for widget in widgets:
                widget.set_range(min=0, max=100)
                try:
                    widget.set_value(default_widget_value)
                except ValueError:
                    widget.set_value(0)

                frame = widget.property('frame')
                if frame is not None:
                    signal = widget.property('signal')
                    signal_path = (frame, signal)
                else:
                    signal_path = tuple(
                        e for e in widget._signal_path if len(e) > 0)

                try:
                    signal = self.neo_frames.signal_by_path(*signal_path)
                except epyqlib.canneo.NotFoundError:
                    if not widget.ignore:
                        widget_path = []
                        p = widget
                        while p is not dash:
                            widget_path.insert(0, p.objectName())
                            p = p.parent()

                        self.dash_missing_signals.add(
                            '{}:/{} - {}'.format(
                                dash.file_name,
                                '/'.join(widget_path),
                                ':'.join(signal_path) if len(signal_path) > 0
                                    else '<none specified>'
                            )
                        )
                else:
                    if signal.frame.id == self.nvs.set_frames[0].id:
                        nv_signal = self.widget_nvs.neo.signal_by_path(*signal_path)

                        if nv_signal.multiplex not in self.nv_looping_reads:
                            def ignore_timeout(failure):
                                if failure.type is \
                                        epyqlib.twisted.nvs.RequestTimeoutError:
                                    return None

                                return epyqlib.utils.twisted.errbackhook(
                                        failure)

                            def read(nv_signal=nv_signal):
                                d = self.nvs.protocol.read(
                                    nv_signal=nv_signal)

                                d.addErrback(ignore_timeout)

                                return d

                            self.nv_looping_reads[nv_signal.multiplex] = read

                        self.nv_looping_set.add_request(
                            key=widget,
                            request=epyqlib.twisted.loopingset.Request(
                                f=self.nv_looping_reads[nv_signal.multiplex],
                                period=1
                            )
                        )

                        if hasattr(widget, 'tx') and widget.tx:
                            signal = self.widget_nvs.neo.signal_by_path(
                                self.nvs.set_frames[0].name, *signal_path[1:])
                        else:
                            signal = self.widget_nvs.neo.signal_by_path(
                                self.nvs.status_frames[0].name, *signal_path[1:])

                    frame = signal.frame
                    frames.add(frame)
                    self.dash_connected_signals.add(signal)
                    widget.set_signal(signal)

                if edit_actions is not None:
                    # TODO: CAMPid 97453289314763416967675427
                    if widget.property('editable'):
                        for action in edit_actions:
                            if action[1](widget):
                                action[0](dash=dash,
                                          widget=widget,
                                          signal=widget.edit)
                                break

        self.bus_status_changed(online=False, transmit=False)

        all_signals = set()
        for frame in self.neo_frames.frames:
            for signal in frame.signals:
                if signal.name != '__padding__':
                    all_signals.add(signal)

        frame_signals = []
        for signal in all_signals - self.dash_connected_signals:
            frame_signals.append('{} : {}'.format(signal.frame.name, signal.name))

        if Elements.nv in self.elements:
            nv_frame_signals = []
            for frame in (list(self.nvs.set_frames.values())
                              + list(self.nvs.status_frames.values())):
                for signal in frame.signals:
                    nv_frame_signals.append(
                        '{} : {}'.format(signal.frame.name, signal.name))

            frame_signals = list(set(frame_signals) - set(nv_frame_signals))

        if len(frame_signals) > 0:
            logger.warning('\n === Signals not referenced by a widget')
            for frame_signal in sorted(frame_signals):
                logger.warning(frame_signal)

        if len(self.dash_missing_signals) > 0:
            logger.error('\n === Signals referenced by a widget but not defined')
            undefined_signals = sorted(self.dash_missing_signals)
            logger.error('\n'.join(undefined_signals))

            box = QMessageBox()
            box.setWindowTitle("EPyQ")

            message = ('The following signals are referenced by the .ui '
                       'files but were not found in the loaded CAN '
                       'database.  The widgets will show `{}`.'
                       .format(default_widget_value))

            message = textwrap.dedent('''\
            {message}

            {signals}
            ''').format(message=message,
                        signals='\n\n'.join(undefined_signals))

            box.setText(message)
            box.exec_()

        self.extension.post()

    def absolute_path(self, path=''):
        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(path).isAbsolute():
            path = os.path.join(
                QFileInfo.absolutePath(QFileInfo(self.config_path)),
                path)

        return path

    def get_frames(self):
        return self.frames

    @pyqtSlot(bool)
    def bus_status_changed(self, online, transmit):
        style = epyqlib.overlaylabel.styles['red']
        text = ''
        if online:
            if not transmit:
                text = 'passive'
                style = epyqlib.overlaylabel.styles['blue']
        else:
            text = 'offline'

        self.ui.offline_overlay.label.setText(text)
        self.ui.offline_overlay.setVisible(len(text) > 0)
        self.ui.offline_overlay.setStyleSheet(style)

    def terminate(self):
        self.neo_frames.terminate()
        self.nv_looping_set.stop()
        logging.debug('{} terminated'.format(object.__repr__(self)))


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
