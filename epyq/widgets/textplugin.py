#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractpluginclass
import epyq.widgets.text

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class TextPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    def __init__(self):
        epyq.widgets.abstractpluginclass.AbstractPlugin.__init__(self)

        self._init = epyq.widgets.text.Text
        self._module_path = 'epyq.widgets.text'
        self._name = 'Text'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
