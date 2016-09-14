import epyq.form
import epyq.abstractpluginclass
import tempfile
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QTimer

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class FormPlugin(epyq.abstractpluginclass.AbstractPlugin):
    def __init__(self, parent=None):
        epyq.abstractpluginclass.AbstractPlugin.__init__(self, parent=parent)

        self._group = 'EPC - General'
        self._init = epyq.form.EpcForm
        self._module_path = 'epyq.form'
        self._name = 'EpcForm'

    def initialize(self, core):
        epyq.abstractpluginclass.AbstractPlugin.initialize(self, core)

        self.filter_widgets()

    def filter_widgets(self):
        widget_box = self.core.widgetBox()

        if widget_box is None:
            QTimer.singleShot(100, self.filter_widgets)
            return

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

    def isContainer(self):
        return True
