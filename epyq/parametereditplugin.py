import functools
import epyq.numberpad
import epyq.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class NumberPadPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=None)

        self._group = 'EPC - General'
        self._init = epyq.numberpad.NumberPad
        self._module_path = 'epyq.numberpad'
        self._name = 'NumberPad'
