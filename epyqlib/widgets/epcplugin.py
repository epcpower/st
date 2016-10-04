#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.abstractsignalpluginclass
import epyqlib.widgets.epc

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class EpcPlugin(epyqlib.widgets.abstractsignalpluginclass.AbstractSignalPlugin):
    def __init__(self, parent=None):
        epyqlib.widgets.abstractsignalpluginclass.AbstractSignalPlugin.__init__(
            self, parent=parent)

        self._init = epyqlib.widgets.epc.Epc
        self._module_path = 'epyqlib.widgets.epc'
        self._name = 'Epc'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
