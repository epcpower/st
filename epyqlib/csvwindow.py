#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import argparse
import csv
import logging
#import math
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

    data = read_csv(args.file.name)

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


def make_chart_view_zoomable(chart):
    filters = []

    f = DoubleClickSignal()
    f.triggered.connect(lambda: _zoom_reset(chart))
    filters.append(f)

    f = ModifierKeySignal()
    f.triggered.connect(lambda *args: _keyboard_modifier(chart, *args))
    filters.append(f)

    for f in filters:
        chart.installEventFilter(f)

    return filters


def _zoom_reset(chart):
    QtCore.QTimer.singleShot(0.2 * 1000, chart.chart().zoomReset)


def _keyboard_modifier(chart, key, pressed):
    mode = QtChart.QChartView.HorizontalRubberBand

    if pressed:
        if key == QtCore.Qt.Key_Shift:
            mode = QtChart.QChartView.VerticalRubberBand
        elif key == QtCore.Qt.Key_Control:
            mode = QtChart.QChartView.RectangleRubberBand

    chart.setRubberBand(mode)


class CheckableChart:
    def __init__(self):
        self.check_box = QtWidgets.QCheckBox()
        self.check_box.setCheckState(QtCore.Qt.Checked)
        self.check_box.stateChanged.connect(self._check_changed)

        self.scaling_spin_box = QtWidgets.QDoubleSpinBox()
        # TODO: set a useful width without limiting the range
        # self.scaling_spin_box.setRange(-math.inf, math.inf)
        self.scaling_spin_box.setRange(-100000, 100000)
        self.scaling_spin_box.setDecimals(3)
        self.scaling_spin_box.setValue(1)
        self.scaling_spin_box.valueChanged.connect(self.scaling_changed)

        self.chart = QtChart.QChart()
        self.series = QtChart.QLineSeries()
        self.chart.addSeries(self.series)
        self.chart.createDefaultAxes()

        # self.chart.plotAreaChanged.connect(self._plot_area_changed)
        self.original_area = None

        self.view = QtChart.QChartView(self.chart)
        self.view_filters = make_chart_view_zoomable(self.view)

        self._name = None
        self.name = '<unnamed>'

        self.data = ()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new):
        self._name = new
        self.check_box.setText(self.name)
        self.series.setName(self.name)

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

    def set_data(self, data):
        self.data = tuple(data)
        self.update()

    def scaling_changed(self, _):
        self.update()

    def update(self):
        scale = self.scaling_spin_box.value()

        self.series.replace(QtGui.QPolygonF((
            QtCore.QPointF(x, y * scale)
            for x, y in self.data
        )))

        if len(self.data) > 0:
            y_minimum = min(y for _, y in self.data) * scale
            y_maximum = max(y for _, y in self.data) * scale

            delta = y_maximum - y_minimum

            if delta == 0:
                extra = 1
            else:
                extra = 0.05 * delta

            self.chart.axisY().setRange(
                y_minimum - extra,
                y_maximum + extra,
            )

            x_minimum = min(x for x, _ in self.data)
            x_maximum = max(x for x, _ in self.data)

            self.chart.axisX().setRange(
                x_minimum,
                x_maximum,
            )


class QtChartWindow(QtWidgets.QMainWindow):
    closing = QtCore.pyqtSignal()

    def __init__(self, data, parent=None):
        super().__init__(parent=parent)

        self.setWindowModality(QtCore.Qt.NonModal)

        self.central_widget = QtWidgets.QWidget()
        self.central_widget_layout = QtWidgets.QVBoxLayout()
        self.scroll_area = QtWidgets.QScrollArea()
        # http://stackoverflow.com/a/27840674/228539
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOn)
        self.central_widget.setLayout(self.central_widget_layout)
        self.central_widget_layout.addWidget(self.scroll_area)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_area.setWidget(self.scroll_widget)

        self.grid_layout = QtWidgets.QGridLayout()
        # self.b1 = QtWidgets.QPushButton()
        # self.b2 = QtWidgets.QPushButton()
        # self.vlayout.addWidget()
        self.scroll_widget.setLayout(self.grid_layout)
        self.setCentralWidget(self.central_widget)

        width = QtWidgets.QApplication.desktop().screenGeometry().width()
        size = self.size()
        size.setWidth(QtWidgets.QDesktopWidget()
                      .availableGeometry(self).size().width() * 0.7)
        size.setHeight(QtWidgets.QDesktopWidget()
                      .availableGeometry(self).size().height() * 0.9)
        self.resize(size)

        # self.charts = []
        # self.views = []
        self.x_axes = []
        # self.y_axes = []
        # self.series = []
        # self.polygons = []
        self.checkable_charts = []

        for name, values in sorted(data.items()):
            if name == '.time':
                continue

            checkable_chart = CheckableChart()
            checkable_chart.name = name
            row = self.grid_layout.rowCount()

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(checkable_chart.check_box)
            layout.addWidget(checkable_chart.scaling_spin_box)
            checkable_chart.scaling_spin_box.setSizePolicy(
                QtWidgets.QSizePolicy.Fixed,
                checkable_chart.scaling_spin_box.sizePolicy().verticalPolicy()
            )

            self.grid_layout.addLayout(
                layout,
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

            if '.time' in data:
                d = zip(data['.time'], values)
            else:
                d = enumerate(values)
            checkable_chart.set_data(data=d)
            self.x_axes.append(chart.axisX())
            self.checkable_charts.append(checkable_chart)

        for axis in self.x_axes:
            axis.rangeChanged.connect(self.axis_range_changed)

    @QtCore.pyqtSlot('qreal', 'qreal')
    def axis_range_changed(self, min, max):
        for axis in self.x_axes:
            axis.setRange(min, max)

    def closeEvent(self, event):
        self.closing.emit()


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
