#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.abstractpluginclass
import os
from PyQt5.QtCore import QFileInfo

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractSignalPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None, in_designer=True):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(
            self,
            parent=parent,
            in_designer=in_designer
        )

        self.in_designer = in_designer

    def createWidget(self, parent):
        return self._init(parent, in_designer=True)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
