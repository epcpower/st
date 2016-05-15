from PyQt5 import QtDesigner
import epyq.svgwidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class SvgWidgetPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
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
        return epyq.svgwidget.SvgWidget(parent)

    def name(self):
        return "SvgWidget"

    def group(self):
        return "Custom"

    # def icon(self):
    #     return QtGui.QIcon(_logo_pixmap)

    def toolTip(self):
        return "SvgWidget widget tool tip"

    def whatsThis(self):
        return "SvgWidget widget what's this"

    def isContainer(self):
        return False

    def domXml(self):
        return (
               '<widget class="SvgWidget" name=\"svg\">\n'
               " <property name=\"toolTip\" >\n"
               "  <string>SVG with utility</string>\n"
               " </property>\n"
               " <property name=\"whatsThis\" >\n"
               "  <string>An SvgWidget</string>\n"
               " </property>\n"
               "</widget>\n"
               )

    def includeFile(self):
        return "epyq.svgwidget"
