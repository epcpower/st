import epyq.widgets.linebar
import epyq.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class LineBarPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Signals'
        self._init = epyq.widgets.linebar.LineBar
        self._module_path = 'epyq.widgets.linebar'
        self._name = 'LineBar'
