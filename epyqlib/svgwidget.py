#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from PyQt5.QtCore import pyqtProperty, QMarginsF, QSize
from PyQt5.QtSvg import QSvgWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class SvgWidget(QSvgWidget):
    def __init__(self, parent=None, in_designer=False):
        QSvgWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        self._main_element = ''

    @pyqtProperty(str)
    def main_element(self):
        return self._main_element

    @main_element.setter
    def main_element(self, id):
        self._main_element = id

        self.update()

    def ratio(self):
        renderer = self.renderer()
        bounds = renderer.boundsOnElement(self.main_element)

        svg_dx = bounds.width()
        svg_dy = bounds.height()

        if svg_dx == 0:
            return 0

        return svg_dy / svg_dx

    def paintEvent(self, event):
        if len(self.main_element) > 0:
            renderer = self.renderer()
            bounds = renderer.boundsOnElement(self.main_element)
            svg_dx = bounds.width()
            svg_dy = bounds.height()
            svg_ratio = svg_dy / svg_dx

            widget_dx = self.width()
            widget_dy = self.height()
            widget_ratio = widget_dy / widget_dx

            if widget_ratio > svg_ratio:
                # widget is taller than svg item so pick taller view
                height = svg_dx * widget_ratio
                extra = (height - svg_dy) / 2
                margins = QMarginsF(0, extra, 0, extra)
            elif widget_ratio < svg_ratio:
                # widget is wider than svg item so pick wider view
                width = svg_dy / widget_ratio
                extra = (width - svg_dx) / 2
                margins = QMarginsF(extra, 0, extra, 0)
            else:
                margins = QMarginsF()

            bounds = bounds.marginsAdded(margins)

            renderer.setViewBox(bounds)

        QSvgWidget.paintEvent(self, event)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
