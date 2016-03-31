#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import canmatrix.importany as importany
import epyq.canneo
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

    def _init_from_file(self, file):
        try:
            zip_file = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            pass
        else:
            self._init_from_zip(zip_file)
            return

        try:
            file = open(file, 'r')
        except TypeError:
            pass
        else:
            self._load_config(file)

            return

        print(file)

    def _load_config(self, file):
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
            name=d.get('name', ''))

    def _init_from_zip(self, zip_file):
        path = tempfile.mkdtemp()
        zip_file.extractall(path=path)

        file = os.path.join(path, 'config.epc')
        file = open(file, 'r')

        self._load_config(file)

        shutil.rmtree(path)

    def _init_from_parameters(self, matrix, ui, serial_number, name, bus=None):
        self.bus = BusProxy(bus=bus)

        self.matrix = matrix
        self.serial_number = serial_number
        self.name = name

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
        self.ui = uic.loadUi(sio)

        self.ui.name.setText(name)

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
