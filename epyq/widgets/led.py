#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyq.widgets.abstractwidget
import os
import re

from PyQt5.QtCore import pyqtProperty, QFile, QFileInfo
from PyQt5.QtGui import QColor
from PyQt5.QtXml import QDomDocument

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def set_attribute_recursive(element, tag_name, attribute,
                            new_color):
    if element.tagName() == tag_name:
        text = element.attribute(attribute)
        text = re.sub('(?<=fill:#)[0-9A-F]{6}', new_color, text)
        element.setAttribute(attribute, text)

    child_nodes = element.childNodes()
    children = [child_nodes.at(i) for i in range(child_nodes.length())]
    for child in children:
        if child.isElement():
            set_attribute_recursive(element=child.toElement(),
                                    tag_name=tag_name,
                                    attribute=attribute,
                                    new_color=new_color)


def make_color(svg_string, new_color):
    doc = QDomDocument()
    doc.setContent(svg_string)
    set_attribute_recursive(element=doc.documentElement(),
                            tag_name="circle",
                            attribute="style",
                            new_color=new_color)

    return doc.toByteArray()


class Led(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'led.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent)

        file_name = 'led.svg'

        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(file_name).isAbsolute():
            file = os.path.join(
                QFileInfo.absolutePath(QFileInfo(__file__)), file_name)
        else:
            file = file_name
        file = QFile(file)
        file.open(QFile.ReadOnly | QFile.Text)
        self.svg_string = file.readAll()

        self._value = False
        self.bright = None
        self.dim = None

        self._color = QColor()
        self.color = QColor("#20C020")

        self._relative_height = 1

        height = self.relative_height * self.ui.label.height()
        ratio = self.ui.value.ratio()

        self.ui.value.setMaximumHeight(height)
        self.ui.value.setMaximumWidth(height / ratio)

        # TODO: shouldn't this be in AbstractWidget?
        self._frame = None
        self._signal = None


    @pyqtProperty(QColor)
    def color(self):
        return self._color

    @color.setter
    def color(self, new_color):
        self._color = QColor(new_color)

        def rgb_string(color):
            return ('{:02X}' * 3).format(*color.getRgb())

        self.bright = make_color(self.svg_string, rgb_string(self._color))

        self.dim = make_color(self.svg_string, rgb_string(
            self._color.darker(factor=200)))

        self.update_svg()

    @pyqtProperty(float)
    def relative_height(self):
        return self._relative_height

    @relative_height.setter
    def relative_height(self, multiplier):
        self._relative_height = multiplier

        height = self.relative_height * self.ui.label.height()
        ratio = self.ui.value.ratio()

        self.ui.value.setMaximumHeight(height)
        self.ui.value.setMinimumHeight(height)

        width = height / ratio
        self.ui.value.setMaximumWidth(width)
        self.ui.value.setMinimumWidth(width)

    def set_value(self, value):
        # TODO: quit hardcoding this and it's better implemented elsewhere
        if self.signal_object is not None:
            value = bool(self.signal_object.value)
        elif value is None:
            value = False
        else:
            value = bool(value)

        self._value = value

        self.update_svg()

    def update_svg(self):
        self.ui.value.load(self.bright if self._value else self.dim)
        self.ui.value.main_element = 'led'


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
