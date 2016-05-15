#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from PyQt5.QtCore import pyqtProperty

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class OverrideRange:
    def __init__(self):
        self._override_range = False

    @pyqtProperty(bool)
    def override_range(self):
        return self._override_range

    @override_range.setter
    def override_range(self, override):
        self._override_range = bool(override)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
