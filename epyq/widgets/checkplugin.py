#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractsignalpluginclass
import epyq.widgets.check

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CheckPlugin(epyq.widgets.abstractsignalpluginclass.AbstractSignalPlugin):
    def __init__(self, parent=None):
        epyq.widgets.abstractsignalpluginclass.AbstractSignalPlugin.__init__(
            self, parent=parent)

        self._init = epyq.widgets.check.Check
        self._module_path = 'epyq.widgets.check'
        self._name = 'Check'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
