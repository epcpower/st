#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import argparse
import csv
import logging
import signal
import sys

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger(__name__)


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--file', '-f', type=argparse.FileType('r'), required=True)

    return parser.parse_args(args)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    args = parse_args(args=args)

    if args.verbose >= 1:
        logger.setLevel(logging.DEBUG)

    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)

    data = read_csv(args.file)

    qtc(data=data)


def read_csv(filename):
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)

        data = {name: [] for name in reader.fieldnames}

        for row in reader:
            for k, v in row.items():
                data[k].append(float(v))

    return data


# class Chart(QtChart.QChart):
#     def mouseDoubleClickEvent(self, event):
#         if event.button() == QtCore.Qt.RightButton:
#             self.zoomReset()
#             return True
#
# class ChartView(QtChart.QChartView):
#     def mouseDoubleClickEvent(self, event):
#         if event.button() == QtCore.Qt.RightButton:
#             self.chart().zoomReset()
#             return True


class DoubleClickSignal(QtCore.QObject):
    triggered = QtCore.pyqtSignal()

    def eventFilter(self, _, event):
        if (isinstance(event, QtGui.QMouseEvent)
                and event.button() == QtCore.Qt.RightButton):
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                self.triggered.emit()
                return True
            # elif event.type() == QtCore.QEvent.MouseButtonPress:
            # elif event.type() == QtCore.QEvent.MouseButtonRelease:

        return False


class ModifierKeySignal(QtCore.QObject):
    triggered = QtCore.pyqtSignal(int, int)
    keys = (QtCore.Qt.Key_Control,
            QtCore.Qt.Key_Shift,
            QtCore.Qt.Key_Alt)

    def eventFilter(self, _, event):
        if isinstance(event, QtGui.QKeyEvent) and event.key() in self.keys:
            self.triggered.emit(
                event.key(),
                event.type() == QtCore.QEvent.KeyPress
            )

        return False


class CheckableChart:
    def __init__(self):
        self.check_box = QtWidgets.QCheckBox()
        self.check_box.setCheckState(QtCore.Qt.Checked)
        self.check_box.stateChanged.connect(self._check_changed)

        self.chart = QtChart.QChart()
        # self.chart.plotAreaChanged.connect(self._plot_area_changed)
        self.original_area = None

        self.view = QtChart.QChartView(self.chart)
        # self.view = ChartView(self.chart)
        self.f = DoubleClickSignal()
        self.f.triggered.connect(self._zoom_reset)
        self.view.installEventFilter(self.f)
        self.g = ModifierKeySignal()
        self.g.triggered.connect(self._keyboard_modifier)
        self.view.installEventFilter(self.g)

        self._name = None
        self.name = '<unnamed>'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new):
        self._name = new
        self.check_box.setText(self.name)

    # def _plot_area_changed(self, area):
    #     if self.original_area is None:
    #         print('changed: {}'.format(area))
    #         self.original_area = area
    #     elif (area.width() > self.original_area.width()
    #             or area.height() > self.original_area.height()):
    #         print('restricted: {}'.format(area))
    #         self.chart.zoomIn(self.original_area)
    #     else:
    #         print('nop: {}'.format(area))

    def _check_changed(self, state):
        self.view.setVisible(state == QtCore.Qt.Checked)

    def _zoom_reset(self):
        QtCore.QTimer.singleShot(0.2 * 1000, self.chart.zoomReset)

    def _keyboard_modifier(self, key, pressed):
        mode = QtChart.QChartView.HorizontalRubberBand

        if pressed:
            if key == QtCore.Qt.Key_Shift:
                mode = QtChart.QChartView.VerticalRubberBand
            elif key == QtCore.Qt.Key_Control:
                mode = QtChart.QChartView.RectangleRubberBand

        self.view.setRubberBand(mode)


class QtChartWindow(QtWidgets.QMainWindow):
    def __init__(self, data, parent):
        super().__init__(parent=parent)

        self.central_widget = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        # self.b1 = QtWidgets.QPushButton()
        # self.b2 = QtWidgets.QPushButton()
        # self.vlayout.addWidget()
        self.central_widget.setLayout(self.grid_layout)
        self.setCentralWidget(self.central_widget)

        width = QtWidgets.QApplication.desktop().screenGeometry().width()
        size = self.size()
        size.setWidth(QtWidgets.QDesktopWidget()
                      .availableGeometry(self).size().width() * 0.7)
        self.resize(size)

        # self.charts = []
        # self.views = []
        self.x_axes = []
        # self.y_axes = []
        # self.series = []
        # self.polygons = []
        self.checkable_charts = []

        for name, values in sorted(data.items()):
            checkable_chart = CheckableChart()
            checkable_chart.name = name
            row = self.grid_layout.rowCount()
            self.grid_layout.addWidget(
                checkable_chart.check_box,
                row,
                0,
                1,
                1,
                QtCore.Qt.AlignLeft
            )
            self.grid_layout.addWidget(
                checkable_chart.view,
                row,
                1
            )

            chart = checkable_chart.chart
            chart.legend().hide()
            view = checkable_chart.view

            view.setRubberBand(QtChart.QChartView.HorizontalRubberBand)
            view.setRenderHint(QtGui.QPainter.Antialiasing)

            x_axis = QtChart.QValueAxis()
            y_axis = QtChart.QValueAxis()
            series = QtChart.QLineSeries()
            series.setName(name)
            m = max(values)
            polygons = QtGui.QPolygonF((QtCore.QPointF(x, y/m) for x, y in enumerate(values)))
            series.append(polygons)
            chart.addAxis(x_axis, QtCore.Qt.AlignBottom)
            chart.addAxis(y_axis, QtCore.Qt.AlignLeft)
            chart.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
            # self.charts.append(chart)
            # self.views.append(view)
            self.x_axes.append(x_axis)
            # self.y_axes.append(y_axis)
            # self.series.append(series)
            # self.polygons.append(polygons)
            self.checkable_charts.append(checkable_chart)

        for axis in self.x_axes:
            axis.rangeChanged.connect(self.axis_range_changed)

    @QtCore.pyqtSlot('qreal', 'qreal')
    def axis_range_changed(self, min, max):
        for axis in self.x_axes:
            axis.setRange(min, max)


def qtc(data):
    app = QtWidgets.QApplication(sys.argv)
    window = QtChartWindow(data=data, parent=None)
    window.show()

    return app.exec()


def _entry_point():
    import traceback

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    def excepthook(excType, excValue, tracebackobj):
        logger.error('Uncaught exception hooked:')
        traceback.print_exception(excType, excValue, tracebackobj)

    sys.excepthook = excepthook
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return main()


if __name__ == '__main__':
    sys.exit(_entry_point())
