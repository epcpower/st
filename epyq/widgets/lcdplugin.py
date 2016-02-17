#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractpluginclass
import epyq.widgets.lcd
import os
from PyQt5.QtCore import QFileInfo

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class LcdPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    _init = epyq.widgets.lcd.Lcd
    _module_path = 'epyq.widgets.lcd'
    _name = 'Lcd'
    _tooltip = 'LCD widget tool tip'
    _whats_this = 'LCD widget what\'s this'
    _icon = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                         '..', 'icon.ico')


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
