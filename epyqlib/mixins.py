#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from PyQt5.QtCore import pyqtProperty

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class OverrideRange:
    def __init__(self):
        self._override_range = False
        self._min = 0
        self._max = 1

    @pyqtProperty(bool)
    def override_range(self):
        return self._override_range

    @override_range.setter
    def override_range(self, override):
        self._override_range = bool(override)

    @pyqtProperty(float)
    def minimum(self):
        return self._min

    @minimum.setter
    def minimum(self, min):
        self._min = float(min)

    @pyqtProperty(float)
    def maximum(self):
        return self._max

    @maximum.setter
    def maximum(self, max):
        self._max = float(max)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
