#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.mixins
import epyqlib.widgets.abstracttxwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class HorizontalSlider(epyqlib.widgets.abstracttxwidget.AbstractTxWidget,
                       epyqlib.mixins.OverrideRange):
    def __init__(self, parent=None, in_designer=False):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'horizontalslider.ui')

        epyqlib.widgets.abstracttxwidget.AbstractTxWidget.__init__(self,
                ui=ui_file, parent=parent, in_designer=in_designer)

        epyqlib.mixins.OverrideRange.__init__(self)

        self._zero_count = None
        self._counts = 1000
        self.ui.value.setTickInterval(self._counts/4)
        self.ui.value.setRange(0, self._counts)

        self.ui.value.valueChanged.connect(self.widget_value_changed)

        self._frame = None
        self._signal = None

    def widget_value_changed(self, counts):
        value = (counts - self._zero_count)
        value *= (self._max - self._min) / self._counts

        epyqlib.widgets.abstracttxwidget.AbstractTxWidget.widget_value_changed(
            self, value)

    def set_value(self, value):
        if value is None:
            value = 0

        counts = (value * self._counts) / (self._max - self._min) + self._zero_count

        self.ui.value.setValue(int(round(counts)))

    # TODO: CAMPid 2397847962541678243196352195498
    def set_range(self, min=None, max=None):
        if self.override_range:
            min = self.minimum
            max = self.maximum

        if min == max:
            # TODO: pick the right exception
            raise Exception('Min and max may not be the same')
        elif min > max:
            # TODO: pick the right exception
            raise Exception('Min must be less than max')

        self._min = min
        self._max = max
        self._zero_count = (0 - min) / (max - min) * self._counts

        if self.signal_object is not None:
            min_string = self.signal_object.format_float(self._min)
            max_string = self.signal_object.format_float(self._max)
        else:
            min_string = ''
            max_string = ''

        self.ui.min.setText(min_string)
        self.ui.max.setText(max_string)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
