#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractpluginclass
import epyq.widgets.enum

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class EnumPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    def __init__(self):
        epyq.widgets.abstractpluginclass.AbstractPlugin.__init__(self)

        self._init = epyq.widgets.enum.Enum
        self._module_path = 'epyq.widgets.enum'
        self._name = 'Enum'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
