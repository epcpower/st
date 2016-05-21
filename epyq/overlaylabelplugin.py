from PyQt5 import QtDesigner
import epyq.overlaylabel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class OverlayLabellugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
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
        return epyq.overlaylabel.OverlayLabel(parent)

    def name(self):
        return "OverlayLabel"

    def group(self):
        return "Custom"

    # def icon(self):
    #     return QtGui.QIcon(_logo_pixmap)

    def toolTip(self):
        return "OverlayLabel widget tool tip"

    def whatsThis(self):
        return "OverlayLabel widget what's this"

    def isContainer(self):
        return False

    def domXml(self):
        return (
               '<widget class="OverlayLabel" name=\"overlaylabel\">\n'
               " <property name=\"toolTip\" >\n"
               "  <string>translucentness</string>\n"
               " </property>\n"
               " <property name=\"whatsThis\" >\n"
               "  <string>An OverlayLabel</string>\n"
               " </property>\n"
               "</widget>\n"
               )

    def includeFile(self):
        return "epyq.overlaylabel"
