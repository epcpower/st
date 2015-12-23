#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import can
import canmatrix.importany as importany
import copy
import epyq.canneo
import epyq.txrx
import math
import os
import platform
from PyQt5 import QtCore, QtWidgets, QtGui, uic
import sys
import time


class Window(QtWidgets.QMainWindow):
    def __init__(self, matrix, tx_model, rx_model, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'main.ui')
        self.ui = uic.loadUi(ui_file, self)
        self.ui.rx.setModel(rx_model)
        self.ui.tx.setModel(tx_model)

        children = self.findChildren(QtCore.QObject)
        targets = [c for c in children if
                   c.property('frame') and c.property('signal')]

        # TODO: make this accessible in Designer
        self.ui.other_scale.setOrientations(QtCore.Qt.Vertical)
        # self.ui.scale.setOrientations(QtCore.Qt.Horizontal)

        for target in targets:
            frame_name = target.property('frame')
            signal_name = target.property('signal')

            frame = matrix.frameByName(frame_name).frame
            signal = frame.frame.signalByName(signal_name).signal
            # TODO: get the frame into the signal constructor where it's called now
            # signal = Signal(frame.frame.signalByName(signal_name), frame)

            breakpoints = [75, 90]
            colors = [QtCore.Qt.darkGreen, QtCore.Qt.darkYellow, QtCore.Qt.darkRed]

            try:
                target.setColorRanges(colors, breakpoints)
            except AttributeError:
                pass

            signal.connect(target.setValue)
            target.setRange(0, 100)#signal._min, signal._max)


def main(args=None):
    import sys

    if args is None:
        import argparse

        can_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..',
            'tests',
            'AFE_CAN_ID247_FACTORY.sym')

        parser = argparse.ArgumentParser()
        parser.add_argument('--can', default=can_file)
        parser.add_argument('--generate', '-g', action='store_true')
        args = parser.parse_args()

    # TODO: get this outta here
    default = {
        'Linux': {'bustype': 'socketcan', 'channel': 'vcan0'},
        'Windows': {'bustype': 'pcan', 'channel': 'PCAN_USBBUS1'}
    }[platform.system()]
    bus = can.interface.Bus(**default)

    # TODO: the repetition here is not so pretty
    matrix_rx = importany.importany(args.can)
    matrix_tx = copy.deepcopy(matrix_rx)
    matrix_widgets = copy.deepcopy(matrix_rx)

    frames_rx = [epyq.txrx.MessageNode(message=None, frame=frame) for frame in matrix_rx._fl._list]
    frames_tx = [epyq.txrx.MessageNode(message=None, frame=frame, tx=True) for frame in matrix_tx._fl._list]

    frames_widgets = [epyq.canneo.Frame(frame) for frame in matrix_widgets._fl._list]
    for frame in frames_widgets:
        [epyq.canneo.Signal(signal, frame=frame) for signal in frame.frame._signals]

    rx = epyq.txrx.TxRx(tx=False, matrix=matrix_rx)
    rx_model = epyq.txrx.TxRxModel(rx)

    rx.changed.connect(rx_model.changed)
    rx.added.connect(rx_model.added)

    tx = epyq.txrx.TxRx(tx=True, matrix=matrix_tx, bus=bus)
    tx_model = epyq.txrx.TxRxModel(tx)

    tx.changed.connect(tx_model.changed)
    tx.added.connect(tx_model.added)
    notifier = can.Notifier(bus, frames_widgets + [rx])

    if args.generate:
        print('generating')
        start_time = time.monotonic()

        frame_name = 'MasterMeasuredPower'
        signal_name = 'ReactivePower_measured'
        frame = epyq.canneo.Frame(matrix_tx.frameByName(frame_name))
        signal = epyq.canneo.Signal(frame.frame.signalByName(signal_name), frame)

        message = can.Message(extended_id=frame.frame._extended,
                              arbitration_id=frame.frame._Id,
                              dlc=frame.frame._Size)

        last_send = 0
        while True:
            time.sleep(0.010)
            now = time.monotonic()
            if now - last_send > 0.100:
                last_send = now
                elapsed_time = time.monotonic() - start_time
                value = math.sin(elapsed_time) / 2
                value += 0.5
                value = round(value * 100)
                print('{:.3f}: {}'.format(elapsed_time, value))
                message.data = frame.pack([0, value])
                bus.send(message)
        sys.exit(0)

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = Window(matrix_widgets, tx_model=tx_model, rx_model=rx_model)

    window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
