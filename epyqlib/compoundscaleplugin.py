import epyqlib.compoundscale
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CompoundScalePlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Compound'
        self._init = epyqlib.compoundscale.CompoundScale
        self._module_path = 'epyqlib.compoundscale'
        self._name = 'CompoundScale'
