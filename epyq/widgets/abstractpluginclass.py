#!/usr/bin/env python3

#TODO: """DocString if there is one"""

from PyQt5 import QtGui, QtDesigner
import textwrap

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
    # https://wiki.python.org/moin/PyQt/Using_Python_Custom_Widgets_in_Qt_Designer
    _group = "EPC"
    _icon = None

    def __init__(self, parent=None):
        QtDesigner.QPyDesignerCustomWidgetPlugin.__init__(self)

        self.initialized = False

    def initialize(self, core):
        if self.initialized:
            return

        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def createWidget(self, parent):
        return self._init(parent)

    def name(self):
        return self._name

    def group(self):
        return self._group

    def icon(self):
        if self._icon is not None:
            return QtGui.QIcon(self._icon)
        else:
            QtDesigner.QPyDesignerCustomWidgetPlugin.icon(self)

    def toolTip(self):
        return self._tooltip

    def whatsThis(self):
        return self._whats_this

    def isContainer(self):
        return False

    # def domXml(self):
    #     xml = textwrap.dedent('''\
    #     <widget class="Wrapper" name="wrapper">
    #       <property name="toolTip" >
    #         <string>{tooltip}</string>
    #       </property>
    #       <property name="whatsThis">
    #         <string>{whats_this}</string>
    #       </property>
    #     </widget>
    #     ''').format(tooltip=self._tooltip,
    #                 whats_this=self._whats_this)
    #
    #     return xml

    def includeFile(self):
        return self._module_path


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
