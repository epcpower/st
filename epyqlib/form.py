#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import canmatrix.formats
import epyqlib.canneo
import epyqlib.widgets.abstractwidget
import math
import os
import sys

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
        self.form_window = None

        self.neo = None

        self.setGeometry(0, 0, 640, 480)

        self.update()
        # Total hack, but it 'works'.  Should be in response to widgets
        # being added, or done being added, or...
        if self.in_designer:
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

    def form_window_file_name_changed(self, _):
        self.update()

    def update(self):
        if not self.in_designer:
            return

        from PyQt5.QtDesigner import QDesignerFormWindowInterface

        can_file = self.can_file

        imported = ()
        new_form_window = (
            QDesignerFormWindowInterface.findFormWindow(self))
        if self.neo is None:
            if self.form_window is not None:
                self.form_window.fileNameChanged.disconnect(
                    self.form_window_file_name_changed)

            self.form_window = new_form_window

            if self.form_window is not None:
                self.form_window.fileNameChanged.connect(
                    self.form_window_file_name_changed)

            if self.form_window is not None:
                if not os.path.isabs(can_file):
                    can_file = os.path.join(
                        os.path.dirname(self.form_window.fileName()),
                        can_file
                    )

            try:
                imported = list(canmatrix.formats.loadp(can_file).values())
            except (FileNotFoundError, IsADirectoryError, OSError):
                # Windows raises an OSError for at least my VirtualBox
                # network drive.
                #
                # >>> f = open('W:/t/603/Hydra_06092017 - old\\'); f.close()
                # Traceback (most recent call last):
                #   File "<stdin>", line 1, in <module>
                # OSError: [Errno 22] Invalid argument: 'W:/t/603/Hydra_06092017 - old\\'
                # >>> f = open('C:/t/603/Hydra_06092017 - old\\'); f.close()
                # Traceback (most recent call last):
                #   File "<stdin>", line 1, in <module>
                # FileNotFoundError: [Errno 2] No such file or directory: 'C:/t/603/Hydra_06092017 - old\\'

                pass

        widgets = self.findChildren(
                epyqlib.widgets.abstractwidget.AbstractWidget)

        if len(imported) > 0:
            self.neo = epyqlib.canneo.Neo(matrix=imported[0])

        for widget in widgets:
            self.update_widget(widget=widget)

    def update_widget(self, widget):
        if not self.in_designer:
            return

        if self.neo is None:
            widget.set_signal(force_update=True)
        else:
            # TODO: CAMPid 07340793413419714301373147
            widget.set_range(min=0, max=100)
            widget.set_value(math.nan)

            frame = widget.property('frame')
            if frame is not None:
                signal = widget.property('signal')
                signal_path = (frame, signal)
            else:
                signal_path = tuple(
                    e for e in widget._signal_path if len(e) > 0)

            try:
                signal = self.neo.signal_by_path(*signal_path)
            except epyqlib.canneo.NotFoundError:
                pass
            else:
                widget.set_signal(signal)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
