import json

import canmatrix.importany
import twisted.internet.defer

import epyqlib.canneo
import epyqlib.nv
import epyqlib.twisted.nvs
import epyqlib.utils.twisted

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class DeviceExtension:
    def __init__(self, device):
        self.device = device

        self.ui = None
        self.frames_nv = None
        self.nvs = None
        self.nv_protocol = None
        self.transport = None
        self.parameter_dict = None

    def post(self):
        self.device.referenced_files.append(
            self.device.raw_dict['auto_parameters'])

        self.ui = self.device.uis['Factory']
        self.ui.load_parameters_button.clicked.connect(
            self.load_parameters)

        matrix_nv = list(
            canmatrix.importany.importany(self.device.can_path).values())[0]
        self.frames_nv = epyqlib.canneo.Neo(
            matrix=matrix_nv,
            frame_class=epyqlib.nv.Frame,
            signal_class=epyqlib.nv.Nv,
            node_id_adjust=self.device.node_id_adjust
        )
        self.nvs = epyqlib.nv.Nvs(self.frames_nv, self.device.bus)
        self.nv_protocol = epyqlib.twisted.nvs.Protocol()
        from twisted.internet import reactor
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.nv_protocol,
            reactor=reactor,
            bus=self.device.bus)

        parameter_path = self.device.raw_dict['auto_parameters']
        parameter_path = self.device.absolute_path(parameter_path)
        with open(parameter_path, 'r') as file:
            s = file.read()
            self.parameter_dict = json.loads(s)

    def load_parameters(self):
        d = self._load_parameters()
        d.addErrback(epyqlib.utils.twisted.errbackhook)

        return d

    @twisted.internet.defer.inlineCallbacks
    def _load_parameters(self):
        self.nvs.from_dict(self.parameter_dict)
        sent_frames = set()

        parameter_names = [k.split(':') for k in self.parameter_dict.keys()]

        factory_signal_name = 'FactoryAccess'
        try:
            (frame, signal), = (
                (f, s)
                for f, s in parameter_names
                if s == factory_signal_name
            )
        except ValueError:
            pass
        else:
            sent_frames.add(frame)

            signal = self.nvs.signal_from_names(frame, signal)
            yield self.nv_protocol.write(nv_signal=signal)

        for frame, signal in parameter_names:
            if frame not in sent_frames:
                sent_frames.add(frame)

                signal = self.nvs.signal_from_names(frame, signal)
                yield self.nv_protocol.write(nv_signal=signal)
