from PyQt5 import QtDesigner
import epyq.devicetreeview

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class DeviceTreeViewPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
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
        return epyq.devicetreeview.DeviceTreeView(parent)

    def name(self):
        return "DeviceTreeView"

    def group(self):
        return "Custom"

    # def icon(self):
    #     return QtGui.QIcon(_logo_pixmap)

    def toolTip(self):
        return "DeviceTreeView widget tool tip"

    def whatsThis(self):
        return "DeviceTreeView widget what's this"

    def isContainer(self):
        return False

    def domXml(self):
        return (
               '<widget class="DeviceTreeView" name=\"devicetreeview\">\n'
               " <property name=\"toolTip\" >\n"
               "  <string>Buses!</string>\n"
               " </property>\n"
               " <property name=\"whatsThis\" >\n"
               "  <string>A DeviceTreeView</string>\n"
               " </property>\n"
               "</widget>\n"
               )

    def includeFile(self):
        return "epyq.devicetreeview"
