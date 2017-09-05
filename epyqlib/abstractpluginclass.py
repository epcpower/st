#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import functools
import epyqlib.utils.qt
from PyQt5 import QtGui, QtDesigner
import os
from PyQt5.QtCore import QFileInfo, qDebug
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
    # https://wiki.python.org/moin/PyQt/Using_Python_Custom_Widgets_in_Qt_Designer

    def __init__(self, parent=None, in_designer=True):
        QtDesigner.QPyDesignerCustomWidgetPlugin.__init__(self, parent=parent)

        self.in_designer = in_designer

        self._group = "EPC - Signals"
        self._icon = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                             'icon.ico')
        self._init = None
        self._module_path = None
        self._name = None
        self._tooltip = None
        self._whats_this = None

        self.initialized = False

    def initialize(self, core):
        if self.initialized:
            return

        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def createWidget(self, parent):
        return self._init(parent, in_designer=True)

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

    def includeFile(self):
        return self._module_path


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
