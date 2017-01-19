# import epyqlib.delegates
# import epyqlib.txrx
import epyqlib.cmemoryparser
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
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 097347143788543453113499349316
def file_dialog(filters, default=0, save=False):
    # TODO: CAMPid 9857216134675885472598426718023132
    # filters = [
    #     ('EPC Packages', ['epc', 'epz']),
    #     ('All Files', ['*'])
    # ]
    # TODO: CAMPid 97456612391231265743713479129

    filter_strings = ['{} ({})'.format(f[0],
                                       ' '.join(['*.'+e for e in f[1]])
                                       ) for f in filters]
    filter_string = ';;'.join(filter_strings)

    if save:
        dialog = QFileDialog.getSaveFileName
    else:
        dialog = QFileDialog.getOpenFileName

    file = dialog(
            filter=filter_string,
            initialFilter=filter_strings[default])[0]

    if len(file) == 0:
        file = None

    return file


class VariableSelection(QtWidgets.QWidget):
    def __init__(self, parent=None, in_designer=False):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.in_designer = in_designer

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
        self.ui.pull_log_button.clicked.connect(self.pull_log)
        self.ui.pull_raw_log_button.clicked.connect(self.pull_raw_log)

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
        filename = file_dialog(filters, save=True)

        if filename is not None:
            model = self.nonproxy_model()
            model.save_selection(filename=filename)

    def load_selection(self):
        filters = [
            ('EPC Variable Selection', ['epv']),
            ('All Files', ['*'])
        ]
        filename = file_dialog(filters)

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
        filename = file_dialog(filters)

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
            d.addErrback(epyqlib.utils.twisted.errbackhook)

    def update_parameters(self):
        model = self.nonproxy_model()
        model.update_parameters()

    def pull_log(self):
        filters = [
            ('CSV', ['csv']),
            ('All Files', ['*'])
        ]
        filename = file_dialog(filters, save=True)

        if filename is not None:
            # TODO: CAMPid 9632763567954321696542754261546
            self.progress = QProgressDialog(self)
            flags = self.progress.windowFlags()
            flags &= ~Qt.WindowContextHelpButtonHint
            self.progress.setWindowFlags(flags)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setAutoReset(False)
            self.progress.setCancelButton(None)

            model = self.nonproxy_model()
            model.pull_log_progress.connect(
                progress=self.progress,
                label_text=('Pulling log...\n\n'
                            + model.pull_log_progress.default_progress_label)
            )
            model.pull_log(csv_path=filename)

    def pull_raw_log(self):
        filters = [
            ('Raw', ['raw']),
            ('All Files', ['*'])
        ]
        filename = file_dialog(filters, save=True)

        if filename is not None:
            # TODO: CAMPid 9632763567954321696542754261546
            self.progress = QProgressDialog(self)
            flags = self.progress.windowFlags()
            flags &= ~Qt.WindowContextHelpButtonHint
            self.progress.setWindowFlags(flags)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setAutoReset(False)
            self.progress.setCancelButton(None)

            model = self.nonproxy_model()
            model.pull_log_progress.connect(
                progress=self.progress,
                label_text=('Pulling log...\n\n'
                            + model.pull_log_progress.default_progress_label)
            )
            model.pull_raw_log(path=filename)

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
