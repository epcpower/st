import epyq.widgets.circularprogressbar
import epyq.abstractpluginclass

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CircularProgressBarPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - Signals'
        self._init = epyq.widgets.circularprogressbar.CircularProgressBar
        self._module_path = 'epyq.widgets.circularprogressbar'
        self._name = 'CircularProgressBar'

    def isContainer(self):
        return True
