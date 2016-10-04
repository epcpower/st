import epyqlib.iogroup
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class IoGroupPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Compound'
        self._init = epyqlib.iogroup.IoGroup
        self._module_path = 'epyqlib.iogroup'
        self._name = 'IoGroup'
