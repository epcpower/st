import collections
import enum
import json

import canmatrix.formats
import twisted.internet.defer

import PyQt5.QtWidgets

import epyqlib.canneo
import epyqlib.nv
import epyqlib.pm.valuesetmodel
import epyqlib.twisted.nvs
import epyqlib.utils.qt
import epyqlib.utils.twisted

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class ConfigurationError(Exception):
    pass


class ValueTypes(enum.Enum):
    parameters = 'auto_parameters'
    value_set = 'auto_value_set'


def value_file(raw_dict):
    paths = {
        value_type: raw_dict[value_type.value]
        for value_type in ValueTypes
        if value_type.value in raw_dict
    }

    try:
        (value_type, path), = paths.items()
    except ValueError as e:
        raise ConfigurationError(
            'Expected one value file but got {}'.format(paths),
        ) from e

    return value_type, path


def referenced_files(raw_dict):
    return value_file(raw_dict)[1]


class DeviceExtension:
    def __init__(self, device):
        self.device = device

        self.ui = None
        self.frames_nv = None
        self.nvs = None
        self.nv_protocol = None
        self.transport = None
        self.parameter_dict = None
        self.progress = None
        self.value_type = None
        self.parameter_names = None
        self.metas = None

    def post(self):
        self.value_type, parameter_path = value_file(self.device().raw_dict)
        parameter_path = self.device().absolute_path(parameter_path)

        self.ui = self.device().uis['Factory']
        self.ui.load_parameters_button.clicked.connect(
            self.load_parameters)

        matrix_nv = list(
            canmatrix.formats.loadp(self.device().can_path).values())[0]
        self.frames_nv = epyqlib.canneo.Neo(
            matrix=matrix_nv,
            frame_class=epyqlib.nv.Frame,
            signal_class=epyqlib.nv.Nv,
            node_id_adjust=self.device().node_id_adjust,
            strip_summary=False,
        )
        self.nvs = epyqlib.nv.Nvs(
            neo=self.frames_nv,
            bus=self.device().bus,
            configuration=self.device().raw_dict['nv_configuration'],
        )
        self.nv_protocol = epyqlib.twisted.nvs.Protocol()
        from twisted.internet import reactor
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.nv_protocol,
            reactor=reactor,
            bus=self.device().bus)

        if self.value_type == ValueTypes.parameters:
            with open(parameter_path, 'r') as file:
                s = file.read()
                self.parameter_dict = json.loads(
                    s, object_pairs_hook=collections.OrderedDict
                )

            self.nvs.from_dict(self.parameter_dict)
            self.parameter_names = [k.split(':') for k in self.parameter_dict.keys()]
            self.metas = (epyqlib.nv.MetaEnum.value,)
        elif self.value_type == ValueTypes.value_set:
            value_set = epyqlib.pm.valuesetmodel.loadp(parameter_path)
            self.nvs.from_value_set(value_set)
            self.parameter_names = [
                node.name.split(':')
                for node in value_set.model.root.leaves()
            ]
            self.metas = epyqlib.nv.meta_limits_first

    def load_parameters(self):
        d = self._load_parameters()
        self._started()
        d.addBoth(epyqlib.utils.twisted.detour_result, self._ended)
        d.addCallback(epyqlib.utils.twisted.detour_result, self._finished)
        d.addErrback(epyqlib.utils.twisted.errbackhook)

    def _started(self):
        self.progress = epyqlib.utils.qt.Progress()
        self.progress.connect(
            progress=epyqlib.utils.qt.progress_dialog(parent=self.device().ui),
            label_text='Writing to device...',
        )

    def _ended(self):
        if self.progress is not None:
            self.progress.complete()
            self.progress = None

    def _finished(self):
        epyqlib.utils.qt.dialog(
            parent=self.device().ui,
            message='Parameters successfully written to device and saved to NV',
            icon=PyQt5.QtWidgets.QMessageBox.Information,
        )

    @twisted.internet.defer.inlineCallbacks
    def _load_parameters(self):
        def node_path(node):
            return [
                node.frame.name,
                node.frame.mux_name,
                node.name,
            ]

        access_level_path = node_path(self.nvs.access_level_node)
        password_path = node_path(self.nvs.password_node)

        paths = (access_level_path, password_path)
        elevate_access_level = all(
            x[1:] in self.parameter_names
            for x in paths
        )

        if elevate_access_level:
            yield self.nv_protocol.write_multiple(
                nv_signals=(
                    self.nvs.access_level_node,
                    self.nvs.password_node,
                ),
                meta=epyqlib.nv.MetaEnum.value,
            )

        selected_nodes = tuple(
            self.nvs.signal_from_names(f, s)
            for f, s in self.parameter_names
            if f != access_level_path[1]
        )
        yield self.nvs.write_all_to_device(
            only_these=selected_nodes,
            meta=self.metas,
        )

        if elevate_access_level:
            self.nvs.access_level_node.set_value(value=0)
            yield self.nv_protocol.write(
                nv_signal=self.nvs.access_level_node,
                meta=epyqlib.nv.MetaEnum.value,
            )

        yield self._module_to_nv()

    def _module_to_nv(self):
        self.nvs.save_signal.set_value(self.nvs.save_value)
        self.nvs.save_frame.update_from_signals()
        d = self.nv_protocol.write(
            nv_signal=self.nvs.save_signal,
            passive=True,
            meta=epyqlib.nv.MetaEnum.value,
        )
        d.addBoth(
            epyqlib.utils.twisted.detour_result,
            self.nvs.module_to_nv_off,
        )

        return d

    def _module_to_nv_off(self):
        self.save_signal.set_value(not self.save_value)
        d = self.protocol.write(self.save_signal, passive=True)

        return d
