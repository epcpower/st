import epyqlib.widgets.linebar
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class LineBarPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Signals'
        self._init = epyqlib.widgets.linebar.LineBar
        self._module_path = 'epyqlib.widgets.linebar'
        self._name = 'LineBar'
