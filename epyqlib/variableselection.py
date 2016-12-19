# import epyqlib.delegates
# import epyqlib.txrx
import io
import os
from PyQt5 import QtWidgets, uic
# from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import QFile, QFileInfo, QTextStream, QSortFilterProxyModel
from PyQt5.QtWidgets import QFileDialog

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
            model = self.nonproxy_model()
            model.load_binary(filename)

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
            model = self.nonproxy_model()
            d = model.pull_log(csv_path=filename)
            d.addErrback(print)
