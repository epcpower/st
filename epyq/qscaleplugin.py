from PyQt5 import QtDesigner
import epyq.qscale

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class QScalePlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
    # https://wiki.python.org/moin/PyQt/Using_Python_Custom_Widgets_in_Qt_Designer

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
        return epyq.qscale.QScale(parent)

    def name(self):
        return "QScale"

    def group(self):
        return "Custom"

    # def icon(self):
    #     return QtGui.QIcon(_logo_pixmap)

    def toolTip(self):
        return "QScale widget tool tip"

    def whatsThis(self):
        return "QScale widget what's this"

    def isContainer(self):
        return False

    def domXml(self):
        return (
               '<widget class="QScale" name=\"scale\">\n'
               " <property name=\"toolTip\" >\n"
               "  <string>analog simplicity</string>\n"
               " </property>\n"
               " <property name=\"whatsThis\" >\n"
               "  <string>A PyQScale</string>\n"
               " </property>\n"
               "</widget>\n"
               )

    def includeFile(self):
        return "epyq.qscale"
