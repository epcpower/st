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
    return value_file(raw_dict)[1:2]


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

        access_level_path = self.device().raw_dict['access_level_path']
        if access_level_path is not None:
            access_level_path = access_level_path.split(';')
        access_password_path = self.device().raw_dict['access_password_path']
        if access_password_path is not None:
            access_password_path = access_password_path.split(';')

        # TODO: CAMPid 0794311304143707516085683164039671793972
        if self.device().raw_dict['nv_meta_enum'] == 'Meta':
            self.metas = epyqlib.nv.meta_limits_first
        else:
            self.metas = (epyqlib.nv.MetaEnum.value,)

        self.nvs = epyqlib.nv.Nvs(
            neo=self.frames_nv,
            bus=self.device().bus,
            configuration=self.device().raw_dict['nv_configuration'],
            metas=self.metas,
            access_level_path=access_level_path,
            access_password_path=access_password_path,
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
        elif self.value_type == ValueTypes.value_set:
            value_set = epyqlib.pm.valuesetmodel.loadp(parameter_path)
            self.nvs.from_value_set(value_set)
            self.parameter_names = [
                node.name.split(':')
                for node in value_set.model.root.leaves()
            ]

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
        access_nodes = tuple(
            node
            for node in (
                self.nvs.password_node,
                self.nvs.access_level_node,
            )
            if node is not None
        )

        import attr
        def s(node, f):
            if f.name == 'value':
                meta = node
            else:
                meta = getattr(node.meta, f.name)

            return str(meta.value)

        def p(nodes, i):
            print('writing {}: '.format(i))
            for node in nodes:
                print(
                    '    {} --- {}'.format(
                        node,
                        ', '.join(
                            s(node, f)
                            for f in attr.fields(type(node.meta))
                        ),
                    )
                )

        p(access_nodes, 1)
        yield self.nvs.write_all_to_device(
            only_these=access_nodes,
            meta=(epyqlib.nv.MetaEnum.value,),
        )

        selected_nodes = set(self.nvs.all_nv()) - set(access_nodes)
        p(selected_nodes, 2)
        yield self.nvs.write_all_to_device(
            only_these=selected_nodes,
            meta=self.metas,
        )

        node_value_backups = []
        for node in access_nodes:
            node_value_backups.append((node, node.value))
            node.set_value(value=0)

        p(access_nodes, 3)
        yield self.nvs.write_all_to_device(
            only_these=access_nodes,
            meta=(epyqlib.nv.MetaEnum.value,),
        )

        for node, value in node_value_backups:
            node.set_value(value=value)

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
