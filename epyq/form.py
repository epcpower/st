#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import canmatrix.importany as importany
import epyq.canneo
import epyq.widgets.abstractwidget
import os
import tempfile
import xml.etree.ElementTree as ET

from PyQt5.QtCore import pyqtProperty, QTimer
from PyQt5.QtDesigner import QDesignerFormWindowInterface
from PyQt5.QtWidgets import QWidget

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class EpcForm(QWidget):
    def __init__(self, parent=None, in_designer=False):
        self.in_designer = in_designer
        QWidget.__init__(self, parent=parent)

        self._can_file = ''
        self.form_window = None

        self.neo = None

        self.setGeometry(0, 0, 640, 480)

        self.update()
        # Total hack, but it 'works'.  Should be in response to widgets
        # being added, or done being added, or...
        QTimer.singleShot(1000, self.update)

    @pyqtProperty(str)
    def can_file(self):
        return self._can_file

    @can_file.setter
    def can_file(self, file):
        self._can_file = file

        self.update()

    @pyqtProperty(bool)
    def update_from_can_file(self):
        return False

    @update_from_can_file.setter
    def update_from_can_file(self, _):
        print('updating now')

        self.update()

    def form_window_file_name_changed(self, _):
        self.update()

    def update(self):
        if not self.in_designer:
            return

        can_file = self.can_file

        new_form_window = (
            QDesignerFormWindowInterface.findFormWindow(self))
        if new_form_window != self.form_window:
            if self.form_window is not None:
                self.form_window.fileNameChanged.disconnect(
                    self.form_window_file_name_changed)

            self.form_window = new_form_window

            if self.form_window is not None:
                self.form_window.fileNameChanged.connect(
                    self.form_window_file_name_changed)

                # `self.in_designer` is the form editor passed to:
                #   QDesignerCustomWidgetInterface::initialize()
                editor = self.in_designer
                widget_box = editor.widgetBox()

                with tempfile.NamedTemporaryFile(mode='r') as temp_original:
                    # Designer will write to the file so we don't need mode='w'
                    widget_box.setFileName(temp_original.name)
                    widget_box.save()

                    tree = ET.parse(temp_original.name)
                    root = tree.getroot()

                    # http://stackoverflow.com/a/2170994/228539
                    parent_map = dict(
                        (c, p) for p in tree.getiterator() for c in p)

                    skip_category_names = ['EPC - General']
                    skip_categories = []
                    for category in root.iter('category'):
                        if category.attrib['name'] in skip_category_names:
                            skip_categories.append(category)

                    for category in skip_categories:
                        parent_map[category].remove(category)

                    skip_entry_names = ['OpenGL Widget']
                    skip_entries = []
                    for entry in root.iter('categoryentry'):
                        if entry.attrib['name'] in skip_entry_names:
                            skip_entries.append(entry)

                    for entry in skip_entries:
                        parent_map[entry].remove(entry)

                    with tempfile.NamedTemporaryFile() as temp_modified:
                        tree.write(temp_modified)
                        with open(temp_modified.name, 'r') as t:
                            for line in t.readlines():
                                print(line, end='')

                            print()

                        widget_box.setFileName(temp_modified.name)
                        loaded = widget_box.load()
                        print('loaded: {}'.format(loaded))

        if self.form_window is not None:
            if not os.path.isabs(can_file):
                can_file = os.path.join(
                    os.path.dirname(self.form_window.fileName()),
                    can_file
                )

        imported = list(importany.importany(can_file).values())

        widgets = self.findChildren(
                epyq.widgets.abstractwidget.AbstractWidget)

        try:
            matrix = imported[0]
        except IndexError:
            self.neo = None
        else:
            self.neo = epyq.canneo.Neo(matrix=matrix)

        for widget in widgets:
            self.update_widget(widget=widget)

    def update_widget(self, widget):
        if not self.in_designer:
            return

        print(widget)
        if self.neo is None:
            widget.set_signal(force_update=True)
        else:
            frame_name = widget.property('frame')
            signal_name = widget.property('signal')

            widget.set_range(min=0, max=100)
            widget.set_value(42)

            # TODO: add some notifications
            frame = self.neo.frame_by_name(frame_name)
            if frame is not None:
                signal = frame.signal_by_name(signal_name)
                if signal is not None:
                    widget.set_signal(signal)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
