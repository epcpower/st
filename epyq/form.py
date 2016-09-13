#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import canmatrix.importany as importany
import epyq.canneo
import epyq.widgets.abstractwidget

from PyQt5.QtCore import pyqtProperty, QTimer
from PyQt5.QtWidgets import QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class EpcForm(QWidget):
    def __init__(self, parent=None, in_designer=False):
        self.in_designer = in_designer
        QWidget.__init__(self, parent=parent)

        self._can_file = ''

        self.neo = None

        self.setGeometry(0, 0, 640, 480)

        self.update()
        # Total hack, but it 'works'.  Should be in response to widgets
        # being added, or done being added, or...
        QTimer.singleShot(1000, self.update)

    @pyqtProperty(str)
    def can_file(self):
        return self._can_file

    @can_file.setter
    def can_file(self, file):
        self._can_file = file

        self.update()

    @pyqtProperty(bool)
    def update_from_can_file(self):
        return False

    @update_from_can_file.setter
    def update_from_can_file(self, _):
        print('updating now')

        self.update()

    def update(self):
        if not self.in_designer:
            return

        imported = list(importany.importany(self.can_file).values())

        widgets = self.findChildren(
                epyq.widgets.abstractwidget.AbstractWidget)

        try:
            matrix = imported[0]
        except IndexError:
            self.neo = None
        else:
            self.neo = epyq.canneo.Neo(matrix=matrix)

        for widget in widgets:
            self.update_widget(widget=widget)

    def update_widget(self, widget):
        if not self.in_designer:
            return

        print(widget)
        if self.neo is None:
            widget.set_signal(force_update=True)
        else:
            frame_name = widget.property('frame')
            signal_name = widget.property('signal')

            widget.set_range(min=0, max=100)
            widget.set_value(42)

            # TODO: add some notifications
            frame = self.neo.frame_by_name(frame_name)
            if frame is not None:
                signal = frame.signal_by_name(signal_name)
                if signal is not None:
                    widget.set_signal(signal)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
