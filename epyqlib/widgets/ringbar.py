#!/usr/bin/env python3

# TODO: """DocString if there is one"""

import epyqlib.widgets.abstractwidget

from PyQt5.QtCore import pyqtProperty, pyqtSlot, QRectF, Qt
from PyQt5.QtGui import QPainter, QPen, QColor

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def arc_angle(angle):
    # Qt expects 1/16 of a degree
    # http://doc.qt.io/qt-5/qpainter.html#drawArc

    return round(16 * angle)


class RingBar(epyqlib.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None, in_designer=False):
        self.in_designer = in_designer
        epyqlib.widgets.abstractwidget.AbstractWidget.__init__(self, parent=parent)

        self._background_color = QColor('#474747')
        self._clockwise = False
        self._color = QColor('#39C550')
        self._maximum = 100
        self._minimum = 0
        self._thickness = 10
        self._value = 75

        self._zero_angle = 0
        self._angle_span = 360

        self._override_range = False

    # TODO  use actual OverrideRange mixin
    @pyqtProperty(bool)
    def override_range(self):
        return self._override_range

    @override_range.setter
    def override_range(self, override):
        self._override_range = bool(override)

    @pyqtProperty(bool)
    def clockwise(self):
        return self._clockwise

    @clockwise.setter
    def clockwise(self, clockwise):
        self._clockwise = clockwise

        self.update()

    @pyqtProperty(float)
    def zero_angle(self):
        return self._zero_angle

    @zero_angle.setter
    def zero_angle(self, angle):
        self._zero_angle = angle

        self.update()

    @pyqtProperty(float)
    def angle_span(self):
        return self._angle_span

    @angle_span.setter
    def angle_span(self, angle):
        self._angle_span = angle

        self.update()

    @pyqtProperty(float)
    def thickness(self):
        return self._thickness

    @thickness.setter
    def thickness(self, thickness):
        self._thickness = thickness

        self.update()

    @pyqtProperty('QColor')
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = QColor(color)

        self.update()

    @pyqtProperty('QColor')
    def background_color(self):
        return self._background_color

    @background_color.setter
    def background_color(self, color):
        self._background_color = QColor(color)

        self.update()

    def dimension(self):
        return min(self.width(), self.height())

    def resizeEvent(self, event):
        epyqlib.widgets.abstractwidget.AbstractWidget.resizeEvent(self, event)

        self.update_layout()

    def tweaked_thickness(self):
        return self.thickness + 1

    def paintEvent(self, event):
        epyqlib.widgets.abstractwidget.AbstractWidget.paintEvent(self, event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.translate(self.width() / 2, self.height() / 2)

        diameter = self.dimension() - self.tweaked_thickness()
        radius = diameter / 2

        rectangle = QRectF(-radius, -radius,
                           diameter, diameter)

        maximum = max(abs(self.maximum), abs(self.minimum))

        span_angle = self.angle_span * (self.value / maximum)

        if self.clockwise:
            span_angle = -span_angle

        pen = QPen()
        pen.setWidthF(self.tweaked_thickness())
        pen.setCapStyle(Qt.RoundCap)

        pen.setColor(self.background_color)
        painter.setPen(pen)
        painter.drawEllipse(rectangle)

        pen.setColor(self.color)
        painter.setPen(pen)

        qt_span = arc_angle(span_angle)
        if qt_span == 0:
            qt_span = 1

        painter.drawArc(rectangle,
                        arc_angle(self.zero_angle),
                        qt_span)

    def update_layout(self):
        horizontal_margin = (self.width() - self.dimension()) / 2
        vertical_margin = (self.height() - self.dimension()) / 2

        horizontal_margin += self.thickness
        vertical_margin += self.thickness

        self.setContentsMargins(horizontal_margin,
                                vertical_margin,
                                horizontal_margin,
                                vertical_margin)

    def update(self):
        self.update_layout()

        epyqlib.widgets.abstractwidget.AbstractWidget.update(self)

    @pyqtSlot(float)
    def set_value(self, value):
        self.value = value

    @pyqtProperty(float)
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

        self.update()

    @pyqtProperty(float)
    def maximum(self):
        return self._maximum

    @maximum.setter
    def maximum(self, maximum):
        self._maximum = maximum

        self.update()

    @pyqtProperty(float)
    def minimum(self):
        return self._minimum

    @minimum.setter
    def minimum(self, minimum):
        self._minimum = minimum

        self.update()

    # TODO: CAMPid 2397847962541678243196352195498
    def set_range(self, min=None, max=None):
        # TODO: stop using min/max
        minimum = min
        maximum = max

        if self.override_range:
            minimum = self.minimum
            maximum = self.maximum

        if minimum == maximum:
            # TODO: pick the right exception
            raise Exception('Min and max may not be the same')
        elif minimum > maximum:
            # TODO: pick the right exception
            raise Exception('Min must be less than max')

        if minimum is not None:
            self.minimum = minimum
        if maximum is not None:
            self.maximum = maximum

    def set_unit_text(self, units):
        pass


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)  # non-zero is a failure
