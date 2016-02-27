from PyQt5 import QtDesigner
import epyq.txrxview

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class TxRxViewPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
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
        return epyq.txrxview.TxRxView(parent)

    def name(self):
        return "TxRxView"

    def group(self):
        return "Custom"

    # def icon(self):
    #     return QtGui.QIcon(_logo_pixmap)

    def toolTip(self):
        return "TxRxView widget tool tip"

    def whatsThis(self):
        return "TxRxView widget what's this"

    def isContainer(self):
        return False

    def domXml(self):
        return (
               '<widget class="TxRxView" name=\"txrxview\">\n'
               " <property name=\"toolTip\" >\n"
               "  <string>canishness</string>\n"
               " </property>\n"
               " <property name=\"whatsThis\" >\n"
               "  <string>A TxRxView</string>\n"
               " </property>\n"
               "</widget>\n"
               )

    def includeFile(self):
        return "epyq.txrxview"
