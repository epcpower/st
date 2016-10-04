import functools
import epyqlib.numberpad
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class NumberPadPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=None)

        self._group = 'EPC - General'
        self._init = epyqlib.numberpad.NumberPad
        self._module_path = 'epyqlib.numberpad'
        self._name = 'NumberPad'
