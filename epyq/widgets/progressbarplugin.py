#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractpluginclass
import epyq.widgets.progressbar

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ProgressBarPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    def __init__(self):
        epyq.widgets.abstractpluginclass.AbstractPlugin.__init__(self)

        self._init = epyq.widgets.progressbar.ProgressBar
        self._module_path = 'epyq.widgets.progressbar'
        self._name = 'ProgressBar'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
