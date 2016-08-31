#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractsignalpluginclass
import epyq.widgets.scale

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ScalePlugin(epyq.widgets.abstractsignalpluginclass.AbstractSignalPlugin):
    def __init__(self, parent=None):
        epyq.widgets.abstractsignalpluginclass.AbstractSignalPlugin.__init__(
            self, parent=parent)

        self._init = epyq.widgets.scale.Scale
        self._module_path = 'epyq.widgets.scale'
        self._name = 'Scale'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
