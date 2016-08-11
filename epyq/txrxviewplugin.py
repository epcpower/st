from PyQt5 import QtDesigner
import epyq.txrxview
import epyq.widgets.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class TxRxViewPlugin(epyq.widgets.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.widgets.abstractpluginclass.AbstractPlugin.__init__(self)

        self._group = 'EPC - General'
        self._init = epyq.txrxview.TxRxView
        self._module_path = 'epyq.txrxview'
        self._name = 'TxRxView'
