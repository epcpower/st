from PyQt5 import QtDesigner
import epyq.listmenuview
import epyq.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class ListMenuViewPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - General'
        self._init = epyq.listmenuview.ListMenuView
        self._module_path = 'epyq.listmenuview'
        self._name = 'ListMenuView'
