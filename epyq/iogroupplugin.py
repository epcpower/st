import epyq.iogroup
import epyq.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class IoGroupPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=None)

        self._group = 'EPC - Compound'
        self._init = epyq.iogroup.IoGroup
        self._module_path = 'epyq.iogroup'
        self._name = 'IoGroup'
