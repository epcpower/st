#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractpluginclass
import epyq.widgets.wrapper
import os
from PyQt5.QtCore import QFileInfo
# from PyQt5.QtCore import pyqtProperty

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class WrapperPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    _init = epyq.widgets.wrapper.Wrapper
    _module_path = 'epyq.widgets.wrapper'
    _name = 'Wrapper'
    _tooltip = 'Wrapper widget tool tip'
    _whats_this = 'Wrapper widget what\'s this'
    _icon = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                         '..', 'icon.ico')
    # _frame = None
    # _signal = None
    # _testy = 'abcdef'

    # @pyqtProperty('QString')
    # def frame(self):
    #     return self._frame
    #
    # @frame.setter
    # def frame(self, frame):
    #     self._frame = frame
    #
    # @pyqtProperty('QString')
    # def signal(self):
    #     return self._signal
    #
    # @signal.setter
    # def frame(self, signal):
    #     self._signal = signal
    #
    # @pyqtProperty('QString')
    # def testy(self):
    #     return self._testy
    #
    # @signal.setter
    # def frame(self, testy):
    #     self._testy = testy


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
