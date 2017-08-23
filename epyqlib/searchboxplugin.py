from PyQt5 import QtDesigner
import epyqlib.searchbox
import epyqlib.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class SearchBoxPlugin(epyqlib.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._group = 'EPC - General'
        self._init = epyqlib.searchbox.SearchBox
        self._module_path = 'epyqlib.searchbox'
        self._name = 'SearchBox'
