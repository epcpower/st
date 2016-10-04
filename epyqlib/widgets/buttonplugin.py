#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.abstractsignalpluginclass
import epyqlib.widgets.button

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ButtonPlugin(epyqlib.widgets.abstractsignalpluginclass.AbstractSignalPlugin):
    def __init__(self, parent=None):
        epyqlib.widgets.abstractsignalpluginclass.AbstractSignalPlugin.__init__(
            self, parent=parent)

        self._init = epyqlib.widgets.button.Button
        self._module_path = 'epyqlib.widgets.button'
        self._name = 'Button'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
