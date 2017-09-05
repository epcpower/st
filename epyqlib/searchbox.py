import os

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import epyqlib.utils.qt

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class SearchBox(QtWidgets.QWidget):
    filter_text_changed = QtCore.pyqtSignal(str)
    filter_requested = QtCore.pyqtSignal()

    search_text_changed = QtCore.pyqtSignal(str)
    search_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None, in_designer=False):
        super().__init__(parent=parent)

        self.in_designer = in_designer

        epyqlib.utils.qt.load_ui(
            os.path.join(os.path.dirname(__file__), 'searchbox.ui'),
            self,
        )

        self._hide_search = False
        self._hide_filter = False
        self.hide_filter = True

        self.search_shortcut = None
        self.view = None

        self.ui_search_text.setPlaceholderText('Search...')
        self.ui_search_text.textChanged.connect(self.search_text_changed)
        self.ui_search_text.returnPressed.connect(self.search_requested)

        self.ui_filter_text.setPlaceholderText('Filter...')
        self.ui_filter_text.textChanged.connect(self.filter_text_changed)
        self.ui_filter_text.textChanged.connect(self.filter_requested)

    @QtCore.pyqtProperty(bool)
    def hide_search(self):
        return self._hide_search

    @hide_search.setter
    def hide_search(self, hide):
        self._hide_search = hide
        self.ui_search_text.setHidden(self.hide_search)

    @QtCore.pyqtProperty(bool)
    def hide_filter(self):
        return self._hide_filter

    @hide_filter.setter
    def hide_filter(self, hide):
        self._hide_filter = hide
        self.ui_filter_text.setHidden(self.hide_filter)

    def focus_search(self):
        self.ui_search_text.setFocus()

    @property
    def search_text(self):
        return self.ui_search_text.text()

    @search_text.setter
    def search_text(self, text):
        self.ui_search_text.setText(text)

    @property
    def filter_text(self):
        return self.ui_filter_text.text()

    @filter_text.setter
    def filter_text(self, text):
        self.ui_filter_text.setText(text)

    def connect_to_view(self, view, column):
        def _search():
            epyqlib.utils.qt.search_view(
                view=view,
                text=self.search_text,
                column=column,
            )
        self.search_requested.connect(_search)

        def _filter():
            view.model().setFilterWildcard(self.filter_text)
        self.filter_requested.connect(_filter)

        self.search_shortcut = QtWidgets.QShortcut(view)
        self.search_shortcut.setKey(QtCore.Qt.CTRL + QtCore.Qt.Key_F)
        self.search_shortcut.activated.connect(self.focus_search)
        self.search_shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
