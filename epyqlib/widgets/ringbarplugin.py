import epyqlib.widgets.ringbar
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class RingBarPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Signals'
        self._init = epyqlib.widgets.ringbar.RingBar
        self._module_path = 'epyqlib.widgets.ringbar'
        self._name = 'RingBar'

    def isContainer(self):
        return True
