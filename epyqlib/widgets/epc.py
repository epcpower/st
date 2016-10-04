#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.abstracttxwidget
import os
from PyQt5.QtCore import (pyqtSignal, pyqtProperty,
                          QFile, QFileInfo, QTextStream, Qt)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Epc(epyqlib.widgets.abstracttxwidget.AbstractTxWidget):
    def __init__(self, parent=None, ui_file='epc.ui', in_designer=False):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               ui_file)

        epyqlib.widgets.abstracttxwidget.AbstractTxWidget.__init__(self,
                ui=ui_file, parent=parent, in_designer=in_designer)

        # TODO: CAMPid 398956661298765098124690765
        self.ui.value.editingFinished.connect(self.widget_value_changed)

        self.ui.edit_button.hide()

        self._frame = None
        self._signal = None

        self._show_enumeration_value = True

        self.update()

    @pyqtProperty(bool)
    def show_enumeration_value(self):
        return self._show_enumeration_value

    @show_enumeration_value.setter
    def show_enumeration_value(self, show):
        self._show_enumeration_value = bool(show)

        self.update()

    def set_signal(self, *args, **kwargs):
        epyqlib.widgets.abstracttxwidget.AbstractTxWidget.set_signal(
            self, *args, **kwargs)

        self.update()

    # TODO: CAMPid 097327143264214321432453216453762354
    def update(self):
        width = self.calculate_max_value_width()
        if width is not None:
            value = self.ui.value
            value.setMinimumWidth(width)

        if self.signal_object is not None:
            alignment = (Qt.AlignRight
                         if len(self.signal_object.enumeration) == 0
                         else Qt.AlignCenter)
            alignment |= Qt.AlignVCenter
            self.ui.value.setAlignment(alignment)


    # TODO: CAMPid 989849193479134917954791341
    def calculate_max_value_width(self):
        if self.signal_object is None:
            return None

        signal = self.signal_object

        longer = max(
            [signal.format_float(v) for v in [signal.min, signal.max]],
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
        strings = [s + '   ' for s in strings]

        return max([metric.width(s) for s in strings])


    def widget_value_changed(self):
        epyqlib.widgets.abstracttxwidget.AbstractTxWidget.widget_value_changed(
            self, self.ui.value.text())

    def set_value(self, value):
        if self.signal_object is not None:
            if len(self.signal_object.enumeration) > 0:
                value = (self.signal_object.full_string
                         if self.show_enumeration_value
                         else self.signal_object.enumeration_text)
            else:
                value = self.signal_object.short_string
        elif value is None:
            # TODO: quit hardcoding this and it's better implemented elsewhere
            value = '{0:.2f}'.format(0)
        else:
            # TODO: quit hardcoding this and it's better implemented elsewhere
            value = '{0:.2f}'.format(value)

        self.ui.value.setText(value)

    @epyqlib.widgets.abstracttxwidget.AbstractTxWidget.tx.setter
    def tx(self, tx):
        epyqlib.widgets.abstracttxwidget.AbstractTxWidget.tx.fset(self, tx)

        self.ui.value.acceptsDrops = self.tx

        self.ui.value.setMouseTracking(self.tx)
        self.ui.value.setReadOnly(not self.tx)
        self.ui.value.setFocusPolicy(Qt.StrongFocus if self.tx else Qt.NoFocus)

        self.update()


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
