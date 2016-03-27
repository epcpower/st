#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import io
import os

from epyq.busproxy import BusProxy
from epyq.widgets.abstractwidget import AbstractWidget
from PyQt5 import uic
from PyQt5.QtCore import QFile, QFileInfo, QTextStream, QObject

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Device:
    def __init__(self, matrix, ui, serial_number, name, bus=None):
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

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
