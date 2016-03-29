#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import can
import canmatrix.importany as importany
import copy
import epyq.busproxy
import epyq.busselector
import epyq.canneo
import epyq.fileselector
import epyq.nv
import epyq.tee
import epyq.txrx
import epyq.widgets.progressbar
import epyq.widgets.lcd
import functools
import io
import math
import os
import platform

from epyq.device import Device

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                          QSettings)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QLabel,
                             QListWidgetItem)
from PyQt5.QtGui import QPixmap
import sys
import time
import traceback

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'

log = open(os.path.join(os.getcwd(), 'epyq.log'), 'w', encoding='utf-8')


# TODO: CAMPid 9756562638416716254289247326327819
class Window(QtWidgets.QMainWindow):
    def __init__(self, ui_file, matrix, tx_model, rx_model, nv_model, bus,
                 devices=[], parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        self.bus = bus

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        self.setWindowIcon(ico)

        ui = ui_file
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

        self.ui.busselector.select_bus.connect(self.select_bus)

        self.ui.rx.setModel(rx_model)
        self.ui.tx.setModel(tx_model)
        try:
            ui_nv = self.ui.nv
        except AttributeError:
            pass
        else:
            ui_nv.setModel(nv_model)

        for device in devices:
            self.ui.stacked.addWidget(device.ui)
            self.ui.stacked.setCurrentWidget(device.ui)
            item = QListWidgetItem(device.name)
            item.setData(QtCore.Qt.UserRole, device.ui)
            self.ui.device_list.addItem(item)
        self.ui.device_list.itemActivated.connect(self.device_activated)

        # TODO: CAMPid 99457281212789437474299
        children = self.findChildren(QtCore.QObject)
        stacked_children = self.ui.stacked.findChildren(QtCore.QObject)
        children = list(set(children) - set(stacked_children))
        widgets = [c for c in children if
                   isinstance(c, epyq.widgets.abstractwidget.AbstractWidget)]
        targets = [c for c in children if
                   c.property('frame') and c.property('signal')]
        targets = list(set(targets) - set(widgets))

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

        try:
            other_scale = self.ui.other_scale
        except AttributeError:
            pass
        else:
            # TODO: make this accessible in Designer
            self.ui.other_scale.setOrientations(QtCore.Qt.Vertical)
            # self.ui.scale.setOrientations(QtCore.Qt.Horizontal)

        for target in targets:
            frame_name = target.property('frame')
            signal_name = target.property('signal')

            frame = matrix.frameByName(frame_name).frame
            signal = frame.frame.signalByName(signal_name).signal

            # TODO: clearly shouldn't be hardcoded
            if frame_name == 'StatusControlVolts2':
                if signal_name == 'n15V_Supply':
                    breakpoints = [-17, -16, -14, -13]
                    colors = [
                        QtCore.Qt.darkRed,
                        QtCore.Qt.darkYellow,
                        QtCore.Qt.darkGreen,
                        QtCore.Qt.darkYellow,
                        QtCore.Qt.darkRed
                    ]
            else:
                breakpoints = [75, 90]
                colors = [QtCore.Qt.darkGreen, QtCore.Qt.darkYellow, QtCore.Qt.darkRed]

            try:
                target.setColorRanges(colors, breakpoints)
            except AttributeError:
                pass

            signal.value_changed.connect(target.setValue)
            target.setRange(float(signal.signal._min),
                            float(signal.signal._max))

    def select_bus(self, interface, channel):
        # TODO: CAMPid 9756652312918432656896822
        if interface != 'offline':
            real_bus = can.interface.Bus(bustype=interface, channel=channel)
        else:
            real_bus = None
        self.bus.set_bus(bus=real_bus)

    def device_activated(self, item):
        device = item.data(QtCore.Qt.UserRole)
        self.ui.stacked.setCurrentWidget(device)


# TODO: Consider updating from...
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/eric6.py#l134

# TODO: deal with licensing for swiped code (GPL3)
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/LICENSE.GPL3

def excepthook(excType, excValue, tracebackobj):
    """
    Global function to catch unhandled exceptions.

    @param excType exception type
    @param excValue exception value
    @param tracebackobj traceback object
    """
    separator = '-' * 70
    email = "kyle.altendorf@epcpower.com"
    notice = \
        """An unhandled exception occurred. Please report the problem via email to:\n"""\
        """\t\t%s\n\n"""\
        """A log has been written to "%s".\n\nError information:\n""" % \
        (email, log.name)
    # TODO: add something for version
    versionInfo=""
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

    tbinfofile = io.StringIO()
    traceback.print_tb(tracebackobj, None, tbinfofile)
    tbinfofile.seek(0)
    tbinfo = tbinfofile.read()
    errmsg = '%s: \n%s' % (str(excType), str(excValue))
    sections = [separator, timeString, separator, errmsg, separator, tbinfo]
    msg = '\n'.join(sections)

    errorbox = QMessageBox()
    errorbox.setWindowTitle("EPyQ FAIL!")
    errorbox.setIcon(QMessageBox.Critical)

    # TODO: CAMPid 980567566238416124867857834291346779
    ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
    ico = QtGui.QIcon(ico_file)
    errorbox.setWindowIcon(ico)

    complete = str(notice) + str(msg) + str(versionInfo)

    sys.stderr.write(complete)
    errorbox.setText(complete)
    errorbox.exec_()


# TODO: CAMPid 907616231629845659923471326
def select_bus():
    bs = epyq.busselector.Selector()
    bs.exec()
    return bs.selected()


# TODO: CAMPid 907616231629845659923471326
def select_recent_file(recent=[]):
    fs = epyq.fileselector.Selector(recent=recent)
    fs.exec()
    return fs.selected()


def main(args=None):
    import sys

    if sys.stdout is None:
        sys.stdout = log
    else:
        sys.stdout = epyq.tee.Tee([sys.stdout, log])
    
    if sys.stderr is None:
        sys.stderr = log
    else:
        sys.stderr = epyq.tee.Tee([sys.stderr, log])
    
    print('starting epyq')

    app = QApplication(sys.argv)
    sys.excepthook = excepthook
    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPyQ')

    settings = QSettings(app.organizationName(),
                         app.applicationName())

    if args is None:
        import argparse

        ui_default = 'main.ui'

        parser = argparse.ArgumentParser()
        parser.add_argument('--can', default=None)

        default_interfaces = {
            'Linux': 'socketcan',
            'Windows': 'pcan'
        }
        parser.add_argument('--interface',
                            default=default_interfaces[platform.system()])

        parser.add_argument('--channel', default=None)
        parser.add_argument('--ui', default=ui_default)
        parser.add_argument('--generate', '-g', action='store_true')
        args = parser.parse_args()

        if args.channel is None:
            interface = 'offline'
            channel = ''
        else:
            interface = args.interface
            channel = args.channel

        recent_can_files = settings.value('recent_can_files', type=str)
        if recent_can_files == '':
            recent_can_files = []

        if args.can is None:
            can_file = ''
            if len(recent_can_files) > 0:
                can_file = select_recent_file(recent_can_files)

                if len(can_file) == 0:
                    # TODO: 8961631268439   use Qt
                    return

            if can_file == '':
                # TODO: CAMPid 97456612391231265743713479129
                can_file = QFileDialog.getOpenFileName(
                        filter='PCAN Symbol (*.sym);; All File (*)',
                        initialFilter='PCAN Symbol (*.sym)')[0]
                if len(can_file) == 0:
                    # TODO: 8961631268439   use Qt
                    return
        else:
            can_file = args.can

    try:
        recent_can_files.remove(can_file)
    except ValueError:
        pass
    recent_can_files.append(can_file)
    recent_can_files = recent_can_files[-10:]
    settings.setValue('recent_can_files', recent_can_files)

    # TODO: CAMPid 9756652312918432656896822
    if interface != 'offline':
        real_bus = can.interface.Bus(bustype=interface, channel=channel)
    else:
        real_bus = None
    bus = epyq.busproxy.BusProxy(bus=real_bus)

    devices = []
    device_frames = []

    matrix_dev1 = list(importany.importany(can_file).values())[0]
    frames_dev1 = epyq.canneo.neotize(matrix=matrix_dev1, bus=bus)
    dev1 = Device(matrix=matrix_dev1,
                  ui='dash1.ui',
                  serial_number=0,
                  name='dev1 name')
    devices.append(dev1)
    device_frames.append(frames_dev1)

    matrix_dev2 = list(importany.importany(can_file).values())[0]
    frames_dev2 = epyq.canneo.neotize(matrix=matrix_dev2, bus=bus)
    dev2 = Device(matrix=matrix_dev2,
                  ui='dash1.ui',
                  serial_number=0,
                  name='dev2 name')
    devices.append(dev2)
    device_frames.append(frames_dev2)

    matrix_dev3 = list(importany.importany(can_file).values())[0]
    frames_dev3 = epyq.canneo.neotize(matrix=matrix_dev3, bus=bus)
    dev3 = Device(matrix=matrix_dev3,
                  ui='dash1.ui',
                  serial_number=0,
                  name='dev3 name')
    devices.append(dev3)
    device_frames.append(frames_dev3)

    # TODO: the repetition here is not so pretty
    matrix_rx = list(importany.importany(can_file).values())[0]
    epyq.canneo.neotize(matrix=matrix_rx,
                        frame_class=epyq.txrx.MessageNode,
                        signal_class=epyq.txrx.SignalNode)

    matrix_tx = list(importany.importany(can_file).values())[0]
    message_node_tx_partial = functools.partial(epyq.txrx.MessageNode,
                                                tx=True)
    signal_node_tx_partial = functools.partial(epyq.txrx.SignalNode,
                                               tx=True)
    epyq.canneo.neotize(matrix=matrix_tx,
                        frame_class=message_node_tx_partial,
                        signal_class=signal_node_tx_partial)

    matrix_widgets = list(importany.importany(can_file).values())[0]
    frames_widgets = epyq.canneo.neotize(
            matrix=matrix_widgets,
            bus=bus)

    rx = epyq.txrx.TxRx(tx=False, matrix=matrix_rx)
    rx_model = epyq.txrx.TxRxModel(rx)

    # TODO: put this all in the model...
    rx.changed.connect(rx_model.changed)
    rx.begin_insert_rows.connect(rx_model.begin_insert_rows)
    rx.end_insert_rows.connect(rx_model.end_insert_rows)

    tx = epyq.txrx.TxRx(tx=True, matrix=matrix_tx, bus=bus)
    tx_model = epyq.txrx.TxRxModel(tx)

    # TODO: put this all in the model...
    tx.changed.connect(tx_model.changed)
    tx.begin_insert_rows.connect(tx_model.begin_insert_rows)
    tx.end_insert_rows.connect(tx_model.end_insert_rows)

    matrix_nv = list(importany.importany(can_file).values())[0]
    epyq.canneo.neotize(
            matrix=matrix_nv,
            frame_class=epyq.nv.Frame,
            signal_class=epyq.nv.Nv)

    notifiees = frames_widgets + [rx]
    notifiees.extend(device_frames)

    try:
        nvs = epyq.nv.Nvs(matrix_nv, bus)
    except epyq.nv.NoNv:
        nv_model = None
    else:
        nv_model = epyq.nv.NvModel(nvs)
        nvs.changed.connect(nv_model.changed)
        notifiees.append(nvs)

    notifier = can.Notifier(bus, notifiees, timeout=0.1)

    if args.generate:
        print('generating')
        start_time = time.monotonic()

        frame_name = 'StatusControlVolts2'
        signal_name = 'n15V_Supply'
        frame = epyq.canneo.Frame(matrix_tx.frameByName(frame_name))
        signal = epyq.canneo.Signal(frame.frame.signalByName(signal_name), frame)

        message = can.Message(extended_id=frame.frame._extended,
                              arbitration_id=frame.frame._Id,
                              dlc=frame.frame._Size)

        messages = [
            can.Message(extended_id=True,
                        arbitration_id=486517239,
                        dlc=8,
                        data=bytearray([0, 1, 0, 160, 7, 208, 5, 220])),
            can.Message(extended_id=True,
                        arbitration_id=486517239,
                        dlc=8,
                        data=bytearray([0, 4, 0, 160, 1, 77, 0, 160])),
            can.Message(extended_id=True,
                        arbitration_id=218082369,
                        dlc=8,
                        data=bytearray([0, 0, 0, 3, 0, 0, 0, 42]))
        ]

        # Copy from PCAN generated and logged messages
        # Bus=2,ID=486517239x,Type=D,DLC=8,DA=0,Data=0 1 0 160 7 208 5 220 ,
        # Bus=2,ID=486517239x,Type=D,DLC=8,DA=0,Data=0 4 0 160 1 77 0 160 ,
        # Bus=2,ID=218082369x,Type=D,DLC=8,DA=0,Data=0 0 0 3 0 0 0 42 ,

        last_send = 0
        while True:
            time.sleep(0.010)
            now = time.monotonic()
            if now - last_send > 0.100:
                last_send = now
                elapsed_time = time.monotonic() - start_time
                value = math.sin(elapsed_time) / 2
                value *= 2
                nominal = -15
                value += nominal
                human_value = value
                value /= float(signal.signal._factor)
                value = round(value)
                print('{:.3f}: {}'.format(elapsed_time, value))
                message.data = frame.pack([value, 0, 1, 2])
                bus.send(message)

                bus.send(can.Message(extended_id=True,
                                     arbitration_id=0xFF9B41,
                                     dlc=8,
                                     data=bytearray([0, 0, 0, 0, 0, 0, 0,
                                         int(human_value > nominal)])))

                for m in messages:
                    bus.send(m)
        sys.exit(0)

    window = Window(ui_file=args.ui, matrix=matrix_widgets,
                    tx_model=tx_model, rx_model=rx_model,
                    nv_model=nv_model, bus=bus, devices=devices)

    window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
