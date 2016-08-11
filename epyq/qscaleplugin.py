from PyQt5 import QtDesigner
import epyq.qscale
import epyq.widgets.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class QScalePlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.widgets.abstractpluginclass.AbstractPlugin.__init__(self)

        self._group = 'EPC - General'
        self._init = epyq.qscale.QScale
        self._module_path = 'epyq.qscale'
        self._name = 'QScale'
