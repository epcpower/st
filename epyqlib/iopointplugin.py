import functools
import epyqlib.iopoint
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class IoPointPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Compound'
        self._init = epyqlib.iopoint.IoPoint
        self._module_path = 'epyqlib.iopoint'
        self._name = 'IoPoint'
