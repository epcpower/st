#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.abstractwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty, QEvent,
                          QFile, QFileInfo, Qt, QTextStream)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Text(epyqlib.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None, in_designer=False):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'text.ui')

        epyqlib.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent, in_designer=in_designer)

        self._frame = None
        self._signal = None

    def set_value(self, value):
        # TODO: quit hardcoding this and it's better implemented elsewhere
        if value is not None:
            value *= self._conversion_multiplier

        if value is None:
            value = '-'
        else:
            if self.signal_object is None:
                value = '{0:.2f}'.format(value)
            elif len(self.signal_object.enumeration) > 0:
                value = self.signal_object.short_string
            else:
                decimal_places = (None
                                  if self.decimal_places < 0
                                  else self.decimal_places)
                value = self.signal_object.format_float(
                    value=value,
                    decimal_places=decimal_places)

        self.ui.value.setText(value)

    def set_signal(self, *args, **kwargs):
        epyqlib.widgets.abstractwidget.AbstractWidget.set_signal(
            self, *args, **kwargs)

        self.update_layout()

    # TODO: CAMPid 097327143264214321432453216453762354
    def update_layout(self):
        width = self.calculate_max_value_width()
        if width is not None:
            self.ui.value.setMinimumWidth(width)

        if self.signal_object is not None:
            alignment = (Qt.AlignRight
                         if len(self.signal_object.enumeration) == 0
                         else Qt.AlignCenter)
            alignment |= Qt.AlignVCenter
            self.ui.value.setAlignment(alignment)

    def event(self, *args, **kwargs):
        result = epyqlib.widgets.abstractwidget.AbstractWidget.event(
            self, *args, **kwargs
        )

        event = args[0]
        if event.type() == QEvent.Polish:
            self.update_layout()

        return result

    # TODO: CAMPid 989849193479134917954791341
    def calculate_max_value_width(self):
        if self.signal_object is None:
            return None

        signal = self.signal_object

        decimal_places = (self.decimal_places
                          if self.decimal_places >= 0
                          else None)

        longer = max(
            [signal.format_float(value=v * self._conversion_multiplier,
                                 decimal_places=decimal_places)
             for v in [signal.min, signal.max]],
            key=len)

        digits = len(longer)

        if '.' in longer:
            decimal = '.'
            digits -= 1
        else:
            decimal = ''

        self.ui.value.setVisible(self.ui.value.isVisibleTo(self))
        metric = self.ui.value.fontMetrics()
        chars = ['{:}'.format(i) for i in range(10)]
        widths = [metric.width(c) for c in chars]
        widest_width = max(widths)
        widest_char = chars[widths.index(widest_width)]
        string = '{}'.format((widest_char * digits) + decimal)

        strings = signal.enumeration_strings()
        strings.append(string)

        # TODO: really figure out the spacing needed but for now
        #       just add a space on each side for buffer space
        strings = [s for s in strings]

        return max([metric.width(s) for s in strings])


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
