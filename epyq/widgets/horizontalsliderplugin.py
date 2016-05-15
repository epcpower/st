#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractpluginclass
import epyq.widgets.horizontalslider

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class HorizontalSliderPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    def __init__(self):
        epyq.widgets.abstractpluginclass.AbstractPlugin.__init__(self)

        self._init = epyq.widgets.horizontalslider.HorizontalSlider
        self._module_path = 'epyq.widgets.horizontalslider'
        self._name = 'HorizontalSlider'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
