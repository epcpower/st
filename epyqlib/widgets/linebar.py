#!/usr/bin/env python3

# TODO: """DocString if there is one"""

import epyqlib.widgets.abstractwidget

from PyQt5.QtCore import pyqtProperty, pyqtSlot, QSizeF, QRectF, Qt
from PyQt5.QtGui import QPainter, QColor

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def centered_rectangle(width, height):
    return QRectF(-width / 2, -height / 2, width, height)


class LineBar(epyqlib.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None, in_designer=False):
        self.in_designer = in_designer
        epyqlib.widgets.abstractwidget.AbstractWidget.__init__(self, parent=parent)

        self._background_color = QColor('#474747')
        self._color = QColor('#39C550')
        self._maximum = 100
        self._minimum = 0
        self._thickness = 10
        self._value = 75

        self._reference_value = 0
        self._reference_marker_size = QSizeF(4, 4)

        self._override_range = False

    # TODO  use actual OverrideRange mixin
    @pyqtProperty(bool)
    def override_range(self):
        return self._override_range

    @override_range.setter
    def override_range(self, override):
        self._override_range = bool(override)

    @pyqtProperty(float)
    def reference_value(self):
        return self._reference_value

    @reference_value.setter
    def reference_value(self, angle):
        self._reference_value = angle

        self.update()

    @pyqtProperty(QSizeF)
    def reference_marker_size(self):
        return self._reference_marker_size

    @reference_marker_size.setter
    def reference_marker_size(self, angle):
        self._reference_marker_size = angle

        self.update_layout()

    @pyqtProperty(float)
    def thickness(self):
        return self._thickness

    @thickness.setter
    def thickness(self, thickness):
        self._thickness = thickness

        self.update_layout()

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

    def paintEvent(self, event):
        epyqlib.widgets.abstractwidget.AbstractWidget.paintEvent(self, event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.translate(self.width() / 2, self.height() / 2)

        painter.fillRect(centered_rectangle(self.thickness, self.height()),
                         self.background_color)

        reference = QRectF(-self.thickness / 2, -self.height() / 2,
                           self.thickness, self.height())

        painter.fillRect(
            centered_rectangle(
                self.thickness + 2 * self.reference_marker_size.width(),
                self.reference_marker_size.height()
            ),
            self.color
        )

        height = ((self.height() / 2)
                  * (self.value - self.reference_value)
                  / (self.maximum - self.reference_value))

        painter.fillRect(
            QRectF(-self.thickness / 2, 0, self.thickness, -height),
            self.color
        )

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
            self._minimum = minimum
        if maximum is not None:
            self._maximum = maximum

    def update_layout(self):
        minimum = self.thickness + 2 * self.reference_marker_size.width()
        self.setMinimumWidth(minimum)

        self.update()

    def set_unit_text(self, units):
        pass


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)  # non-zero is a failure
