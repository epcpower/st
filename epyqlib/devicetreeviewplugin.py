from PyQt5 import QtDesigner
import epyqlib.devicetreeview
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class DeviceTreeViewPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyqlib.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - General'
        self._init = epyqlib.devicetreeview.DeviceTreeView
        self._module_path = 'epyqlib.devicetreeview'
        self._name = 'DeviceTreeView'
