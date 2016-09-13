import epyq.form
import epyq.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class FormPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - General'
        self._init = epyq.form.EpcForm
        self._module_path = 'epyq.form'
        self._name = 'EpcForm'

    def isContainer(self):
        return True
