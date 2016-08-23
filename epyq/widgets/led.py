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


def rgb_string(color):
    return ('{:02X}' * 3).format(*color.getRgb())


class Led(epyq.widgets.abstractwidget.AbstractWidget):
    def __init__(self, parent=None, in_designer=False):
        ui_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                               'led.ui')

        epyq.widgets.abstractwidget.AbstractWidget.__init__(self,
                ui=ui_file, parent=parent, in_designer=in_designer)

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

        # TODO: shouldn't this be in AbstractWidget?
        self._frame = None
        self._signal = None
        self._on_value = 1
        self._relative_height = 1

        self._value = False
        self.svg = {
            'on': None,
            'automatic_off': None,
            'manual_off': None
        }
        self.ui.value.main_element = 'led'

        self._on_color = QColor()
        self._manual_off_color = QColor()
        self._automatic_off_color = True
        self.on_color = QColor("#20C020")
        self.manual_off_color = self.on_color.darker(factor=200)

        self.update_svg()

    @pyqtProperty(int)
    def on_value(self):
        return self._on_value

    @on_value.setter
    def on_value(self, new_on_value):
        new_on_value = int(new_on_value)
        if self._on_value != new_on_value:
            self._on_value = new_on_value
            self.update_svg()

    @pyqtProperty(bool)
    def automatic_off_color(self):
        return self._automatic_off_color

    @automatic_off_color.setter
    def automatic_off_color(self, automatic):
        automatic = bool(automatic)
        if automatic != self._automatic_off_color:
            self._automatic_off_color = bool(automatic)
            self.update_svg()

    @pyqtProperty(QColor)
    def on_color(self):
        return self._on_color

    @on_color.setter
    def on_color(self, new_color):
        self._on_color = QColor(new_color)

        self.svg['on'] = make_color(self.svg_string, rgb_string(self._on_color))

        if self.automatic_off_color:
            self.svg['automatic_off'] = make_color(
                self.svg_string,
                rgb_string(self._on_color.darker(factor=200))
            )

        self.update_svg()

    @pyqtProperty(QColor)
    def manual_off_color(self):
        return self._manual_off_color

    @manual_off_color.setter
    def manual_off_color(self, new_color):
        self._manual_off_color = QColor(new_color)

        self.svg['manual_off'] = make_color(self.svg_string, rgb_string(self._manual_off_color))

        self.update_svg()

    @pyqtProperty(float)
    def relative_height(self):
        return self._relative_height

    @relative_height.setter
    def relative_height(self, multiplier):
        self._relative_height = multiplier

        self.update_svg()

    def set_value(self, value):
        # TODO: quit hardcoding this and it's better implemented elsewhere
        if self.signal_object is not None:
            value = self.signal_object.value
        else:
            value = value

        self._value = (value == self.on_value)

        self.update_svg()

    def update_svg(self):
        if self._value:
            svg = self.svg['on']
        elif self.automatic_off_color:
            svg = self.svg['automatic_off']
        else:
            svg = self.svg['manual_off']

        self.ui.value.load(svg)

        height = self.relative_height * self.ui.label.fontMetrics().height()

        width = height / self.ui.value.ratio()

        self.ui.value.setFixedSize(width, height)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
