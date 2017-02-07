# import epyqlib.delegates
# import epyqlib.txrx
import epyqlib.cmemoryparser
import epyqlib.datalogger
import epyqlib.utils.qt
import epyqlib.utils.twisted
import io
import os
from PyQt5 import QtWidgets, uic
# from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QSortFilterProxyModel,
                          Qt)
from PyQt5.QtWidgets import QFileDialog, QProgressDialog
import twisted.internet.threads

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class VariableSelection(QtWidgets.QWidget):
    def __init__(self, parent=None, in_designer=False):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

        self.device = None

        ui = 'variableselection.ui'
        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(ui).isAbsolute():
            ui_file = os.path.join(
                QFileInfo.absolutePath(QFileInfo(__file__)), ui)
        else:
            ui_file = ui
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly | QFile.Text)
        ts = QTextStream(ui_file)
        sio = io.StringIO(ts.readAll())
        self.ui = uic.loadUi(sio, self)

        self.ui.load_binary_button.clicked.connect(self.load_binary)
        self.ui.save_selection_button.clicked.connect(self.save_selection)
        self.ui.load_selection_button.clicked.connect(self.load_selection)
        self.ui.update_parameters_button.clicked.connect(self.update_parameters)
        self.ui.process_raw_log_button.clicked.connect(self.process_raw_log)
        self.ui.process_raw_log_button.setEnabled(False)

        self.ui.view.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.view.tree_view.customContextMenuRequested.connect(
            self.context_menu
        )

        self.progress = None

    def set_model(self, model):
        self.ui.view.set_model(model)

    def set_sorting_enabled(self, enabled):
        self.ui.view.set_sorting_enabled(enabled)

    def sort_by_column(self, column, order):
        self.ui.view.sort_by_column(column=column, order=order)

    def save_selection(self):
        filters = [
            ('EPC Variable Selection', ['epv']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(filters, save=True)

        if filename is not None:
            model = self.nonproxy_model()
            model.save_selection(filename=filename)

    def load_selection(self):
        filters = [
            ('EPC Variable Selection', ['epv']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(filters)

        if filename is not None:
            model = self.nonproxy_model()
            model.load_selection(filename=filename)

    def nonproxy_model(self):
        model = self.ui.view.model
        while isinstance(model, QSortFilterProxyModel):
            model = model.sourceModel()

        return model

    def load_binary(self):
        filters = [
            ('TICOFF Binaries', ['out']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(filters)

        if filename is not None:
            # TODO: CAMPid 9632763567954321696542754261546
            self.progress = QProgressDialog(self)
            flags = self.progress.windowFlags()
            flags &= ~Qt.WindowContextHelpButtonHint
            self.progress.setWindowFlags(flags)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setAutoReset(False)
            self.progress.setCancelButton(None)
            self.progress.setMinimumDuration(0)
            # Uncertain duration so use a busy indicator
            self.progress.setMinimum(0)
            self.progress.setMaximum(0)
            self.progress.setLabelText('Loading binary...')

            model = self.nonproxy_model()
            model.binary_loaded.connect(self.progress.close)

            self.progress.show()

            d = twisted.internet.threads.deferToThread(
                epyqlib.cmemoryparser.process_file,
                filename=filename
            )
            d.addCallback(model.update_from_loaded_binary)
            d.addCallback(epyqlib.utils.twisted.detour_result,
                          self.ui.process_raw_log_button.setEnabled, True)
            d.addErrback(epyqlib.utils.twisted.errbackhook)

    def update_parameters(self):
        model = self.nonproxy_model()
        model.update_parameters()

    def process_raw_log(self):
        filters = [
            ('Raw', ['raw']),
            ('All Files', ['*'])
        ]
        raw_filename = epyqlib.utils.qt.file_dialog(filters)

        if raw_filename is not None:
            filters = [
                ('CSV', ['csv']),
                ('All Files', ['*'])
            ]
            csv_filename = epyqlib.utils.qt.file_dialog(filters, save=True)

            if csv_filename is not None:
                with open(raw_filename, 'rb') as f:
                    data = f.read()

                model = self.nonproxy_model()

                # TODO: CAMPid 9632763567954321696542754261546
                progress = QProgressDialog(self)
                flags = self.progress.windowFlags()
                flags &= ~Qt.WindowContextHelpButtonHint
                progress.setWindowFlags(flags)
                progress.setWindowModality(Qt.WindowModal)
                progress.setAutoReset(False)
                progress.setCancelButton(None)
                progress.setMinimumDuration(0)
                # Uncertain duration so use a busy indicator
                # TODO: we could actually count records so do that someday
                progress.setMinimum(0)
                progress.setMaximum(0)
                progress.setLabelText('Processing Raw Log...')

                progress.show()

                d = model.parse_log(data=data, csv_path=csv_filename)
                d.addBoth(epyqlib.utils.twisted.detour_result,
                          progress.close)
                d.addErrback(epyqlib.utils.twisted.errbackhook)

    def context_menu(self, position):
        index = self.ui.view.tree_view.indexAt(position)
        index = self.ui.view.tree_view.model().mapToSource(index)

        if not index.isValid():
            return

        node = self.nonproxy_model().node_from_index(index)

        menu = QtWidgets.QMenu()
        read_action = menu.addAction('Read')

        action = menu.exec(
            self.ui.view.tree_view.viewport().mapToGlobal(position))

        if action is None:
            pass
        elif action is read_action:
            self.nonproxy_model().read(variable=node)
