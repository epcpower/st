#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import io
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo, QTextStream
from PyQt5.QtWidgets import QWidget

from compoundscale import CompoundScale
# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CompoundScaleLeft(CompoundScale):
    def __init__(self, parent=None, in_designer=False):
        # QWidget.__init__(self, parent=parent)
        CompoundScale.__init__(self, parent, in_designer)

    def getPath(self):
        return os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                          'compoundscaleleft.ui')
if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
