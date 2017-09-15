import epyqlib.dualscale
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class DualScalePlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Other'
        self._init = epyqlib.dualscale.DualScale
        self._module_path = 'epyqlib.dualscale'
        self._name = 'DualScale'
