import functools
import io
import os
import sys
import textwrap
import time
import traceback

import epyqlib.utils.general

from PyQt5 import QtCore
from PyQt5 import QtWidgets
import PyQt5.uic

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 953295425421677545429542967596754
log = os.path.join(os.getcwd(), 'epyq.log')


_version_tag = None
_build_tag = None
_parent = None


def exception_message_box_register_versions(version_tag, build_tag):
    global _version_tag
    global _build_tag

    _version_tag = version_tag
    _build_tag = build_tag


def exception_message_box_register_parent(parent):
    global _parent

    _parent = parent


def exception_message_box(excType=None, excValue=None, tracebackobj=None):
    def join(iterable):
        return ''.join(iterable).strip()

    brief = join(traceback.format_exception_only(
        etype=excType,
        value=excValue
    ))

    extended = join(traceback.format_exception(
        etype=excType,
        value=excValue,
        tb=tracebackobj,
    ))

    custom_exception_message_box(
        brief=brief,
        extended=extended,
    )


def custom_exception_message_box(brief, extended=''):
    email = "kyle.altendorf@epcpower.com"

    brief = textwrap.dedent('''\
        An unhandled exception occurred. Please report the problem via email to:
                        {email}

        {brief}''').format(
        email=email,
        brief=brief,
    )

    raw_exception_message_box(brief=brief, extended=extended)


def raw_exception_message_box(brief, extended, stderr=True):
    version = ''
    if _version_tag is not None:
        version = 'Version Tag: {}'.format(_version_tag)

    build = ''
    if _build_tag is not None:
        build = 'Build Tag: {}'.format(_build_tag)

    info = (version, build)
    info = '\n'.join(s for s in info if len(s) > 0)
    if len(info) > 0:
        info += '\n\n'

    time_string = time.strftime("%Y-%m-%d, %H:%M:%S %Z")

    details = textwrap.dedent('''\
        {info}A log has been written to "{log}".
        {time_string}''').format(
        info=info,
        log=log,
        time_string=time_string,
    )

    if len(extended) > 0:
        details = '\n'.join(s.strip() for s in (details, '-' * 70, extended))

    if stderr:
        sys.stderr.write('\n'.join((brief, details, '')))

    dialog(
        parent=_parent,
        title='Exception',
        message=brief,
        details=details,
        icon=QtWidgets.QMessageBox.Critical,
    )


# http://stackoverflow.com/a/35902894/228539
def message_handler(mode, context, message):
    mode_strings = {
        QtCore.QtInfoMsg: 'INFO',
        QtCore.QtWarningMsg: 'WARNING',
        QtCore.QtCriticalMsg: 'CRITICAL',
        QtCore.QtFatalMsg: 'FATAL'
    }

    mode = mode_strings.get(mode, 'DEBUG')

    print('qt_message_handler: f:{file} l:{line} f():{function}'.format(
        file=context.file,
        line=context.line,
        function=context.function
    ))
    print('  {}: {}\n'.format(mode, message))


class Progress(QtCore.QObject):
    # TODO: CAMPid 7531968542136967546542452
    updated = QtCore.pyqtSignal(int)
    completed = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()

    default_progress_label = (
        '{elapsed} seconds elapsed, {remaining} seconds remaining'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.completed.connect(self.done)
        self.failed.connect(self.done)
        self.canceled.connect(self.done)

        self.done.connect(self._done)

        self.progress = None
        self.average = None
        self.average_timer = QtCore.QTimer()
        self.average_timer.setInterval(200)
        self.average_timer.timeout.connect(self._update_time_estimate)
        self._label_text_replace = None
        self._start_time = None

    def _done(self):
        self.average_timer.stop()
        self.average = None

        self.updated.disconnect(self.progress.setValue)
        self.progress.close()
        self.progress.deleteLater()
        self.progress = None

        self._start_time = None

    def _update_time_estimate(self):
        remaining = self.average.remaining_time(self.progress.maximum())
        try:
            remaining = round(remaining)
        except:
            pass
        self.progress.setLabelText(self._label_text_replace.format(
                elapsed=round(time.monotonic() - self._start_time),
                remaining=remaining
            )
        )

    def connect(self, progress, label_text=None):
        self.progress = progress

        if label_text is None:
            label_text = self.default_progress_label
        self._label_text_replace = label_text

        self.progress.setMinimumDuration(0)
        self.progress.setValue(0)
        # Default to a busy indicator, progress maximum can be set later
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.updated.connect(self.progress.setValue)

        if self._start_time is None:
            self._start_time = time.monotonic()

        self.average = epyqlib.utils.general.AverageValueRate(seconds=30)
        self.average_timer.start()

    def configure(self, minimum=0, maximum=0):
        self.progress.setMinimum(minimum)
        self.progress.setMaximum(maximum)

    def complete(self, message=None):
        if message is not None:
            QtWidgets.QMessageBox.information(self.progress, 'EPyQ', message)

        self.completed.emit()

    def elapsed(self):
        return time.monotonic() - self._start_time

    def fail(self):
        self.failed.emit()

    def update(self, value):
        self.average.add(value)
        self.updated.emit(value)


def complete_filter_type(extension):
    if extension == '*':
        return extension

    return '*.' + extension

def create_filter_string(name, extensions):
    return '{} ({})'.format(
        name,
        ' '.join((complete_filter_type(e) for e in extensions)),
     )


def file_dialog(filters, default=0, save=False, parent=None):
    # TODO: CAMPid 9857216134675885472598426718023132
    # filters = [
    #     ('EPC Packages', ['epc', 'epz']),
    #     ('All Files', ['*'])
    # ]
    # TODO: CAMPid 97456612391231265743713479129

    filter_strings = [create_filter_string(f[0], f[1]) for f in filters]
    filter_string = ';;'.join(filter_strings)

    if save:
        dialog = QtWidgets.QFileDialog.getSaveFileName
    else:
        dialog = QtWidgets.QFileDialog.getOpenFileName

    file = dialog(
            parent=parent,
            filter=filter_string,
            initialFilter=filter_strings[default])[0]

    if len(file) == 0:
        file = None

    return file


def get_code():
    code = None

    code_file = QtCore.QFile(':/code')
    if code_file.open(QtCore.QIODevice.ReadOnly):
        code = bytes(code_file.readAll())
        code = code.decode('ascii').strip().encode('ascii')
        code_file.close()

    return code


def progress_dialog(parent=None, cancellable=False):
    progress = QtWidgets.QProgressDialog(parent)
    flags = progress.windowFlags()
    flags &= ~QtCore.Qt.WindowContextHelpButtonHint
    flags &= ~QtCore.Qt.WindowCloseButtonHint
    progress.setWindowFlags(flags)
    progress.setWindowModality(QtCore.Qt.WindowModal)
    progress.setAutoReset(False)
    if not cancellable:
        progress.setCancelButton(None)
    progress.setMinimumDuration(0)
    progress.setMinimum(0)
    progress.setMaximum(0)

    return progress


class FittedTextBrowser(QtWidgets.QTextBrowser):
    def sizeHint(self):
        default = super().sizeHint()

        if not default.isValid():
            return default

        document_size = self.document().size()

        desktops = QtWidgets.QApplication.desktop()
        screen_number = desktops.screenNumber(self.parent())
        geometry = desktops.screenGeometry(screen_number)

        if document_size.width() == 0:
            document_size.setWidth(geometry.width() * 0.25)
        if document_size.height() == 0:
            document_size.setHeight(geometry.height() * 0.4)

        scrollbar_width = QtWidgets.QApplication.style().pixelMetric(
            QtWidgets.QStyle.PM_ScrollBarExtent
        )

        width = sum((
            document_size.width(),
            self.contentsMargins().left(),
            self.contentsMargins().right(),
            scrollbar_width,
        ))

        height = sum((
            document_size.height(),
            self.contentsMargins().top(),
            self.contentsMargins().bottom(),
            scrollbar_width,
        ))

        return QtCore.QSize(width, height)


class DialogUi:
    def __init__(self, parent):
        self.layout = QtWidgets.QGridLayout(parent)
        self.icon = QtWidgets.QLabel(parent)
        self.message = FittedTextBrowser(parent)
        self.details = FittedTextBrowser(parent)
        self.copy = QtWidgets.QPushButton(parent)
        self.show_details = QtWidgets.QPushButton(parent)
        self.buttons = QtWidgets.QDialogButtonBox(parent)

        self.copy.setText('Copy To Clipboard')
        self.show_details.setText('Details...')

        self.layout.addWidget(self.icon, 0, 0, 2, 1)
        self.layout.addWidget(self.message, 0, 1, 1, 3)
        self.layout.addWidget(self.details, 1, 1, 1, 3)
        self.layout.addWidget(self.copy, 2, 1)
        self.layout.addWidget(self.show_details, 2, 2)
        self.layout.addWidget(self.buttons, 2, 3)

        self.layout.setColumnStretch(3, 1)


class Dialog(QtWidgets.QDialog):
    def __init__(self, *args, cancellable=False, details=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = DialogUi(parent=self)

        self.ui.details.setVisible(False)
        self.ui.show_details.setVisible(details)

        self.ui.buttons.accepted.connect(self.accept)
        self.ui.buttons.rejected.connect(self.reject)

        self.ui.copy.clicked.connect(self.copy)
        self.ui.show_details.clicked.connect(self.show_details)

        self.setLayout(self.ui.layout)
        buttons = QtWidgets.QDialogButtonBox.Ok
        if cancellable:
            buttons |= QtWidgets.QDialogButtonBox.Cancel

        self.ui.buttons.setStandardButtons(buttons)

        self.text = None
        self.html = None
        self.details_text = None
        self.details_html = None

        desktops = QtWidgets.QApplication.desktop()
        screen_number = desktops.screenNumber(self.parent())
        geometry = desktops.screenGeometry(screen_number)

        self.setMaximumHeight(geometry.height() * 0.7)
        self.setMaximumWidth(geometry.width() * 0.7)
        self.minimum_size = self.minimumSize()
        self.maximum_size = self.maximumSize()

    def copy(self):
        f = textwrap.dedent('''\
            {message}
            
             - - - - Details:
            
            {details}
            '''
        ).format(
            message=self.ui.message.toPlainText(),
            details=self.ui.details.toPlainText(),
        )

        QtWidgets.QApplication.clipboard().setText(f)

    def show_details(self):
        to_be_visible = not self.ui.details.isVisible()
        self.ui.details.setVisible(to_be_visible)
        self.set_size()

    def set_size(self):
        self.setFixedSize(self.sizeHint())
        self.setMinimumSize(self.minimum_size)
        self.setMaximumSize(self.maximum_size)

    def set_text(self, text):
        self.ui.message.setPlainText(text)

        self.html = None
        self.text = text

        self.ui.message.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

    def set_html(self, html):
        self.ui.message.setHtml(html)

        self.html = html
        self.text = None

        self.ui.message.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)

    def set_details_text(self, text):
        self.ui.details.setPlainText(text)

        self.details_html = None
        self.details_text = text

        self.ui.details.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

    def set_details_html(self, html):
        self.ui.details.setHtml(html)

        self.details_html = html
        self.details_text = None

        self.ui.details.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)

    def set_message_box_icon(self, icon):
        self.ui.icon.setPixmap(QtWidgets.QMessageBox.standardIcon(icon))


def dialog(parent, message, title=None, icon=None,
           rich_text=False, details='', details_rich_text=False,
           cancellable=False):
    box = Dialog(
        parent=parent,
        cancellable=cancellable,
        details=len(details) > 0,
    )

    if rich_text:
        box.set_html(message)
    else:
        box.set_text(message)

    if details_rich_text:
        box.set_details_html(details)
    else:
        box.set_details_text(details)

    if icon is not None:
        box.set_message_box_icon(icon)

    if title is not None:
        parent_title = QtWidgets.QApplication.instance().applicationName()

        if len(parent_title) > 0:
            title = ' - '.join((
                parent_title,
                title,
            ))


        box.setWindowTitle(title)

    box.finished.connect(box.deleteLater)

    return box.exec()


def dialog_from_file(parent, title, file_name):
    # The Qt Installer Framework (QtIFW) likes to do a few things to license files...
    #  * '\n' -> '\r\n'
    #   * even such that '\r\n' -> '\r\r\n'
    #  * Recodes to something else (probably cp-1251)
    #
    # So, we'll just try different encodings and hope one of them works.

    encodings = [None, 'utf-8']

    for encoding in encodings:
        try:
            with open(os.path.join('Licenses', file_name), encoding=encoding) as in_file:
                message = in_file.read()
        except UnicodeDecodeError:
            pass
        else:
            break

    dialog(
        parent=parent,
        title=title,
        message=message,
    )


class PySortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, filter_column, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: replace with filterKeyColumn
        self.filter_column = filter_column

        self.wildcard = QtCore.QRegExp()
        self.wildcard.setPatternSyntax(QtCore.QRegExp.Wildcard)

    def lessThan(self, left, right):
        left_model = left.model()
        left_data = (
            left_model.data(left, self.sortRole())
            if left_model else
            None
        )

        right_model = right.model()
        right_data = (
            right_model.data(right, self.sortRole())
            if right_model else
            None
        )

        return left_data < right_data

    def filterAcceptsRow(self, row, parent):
        # TODO: do i need to invalidate any time i set the 'regexp'?
        # http://doc.qt.io/qt-5/qsortfilterproxymodel.html#invalidateFilter

        pattern = self.filterRegExp().pattern()
        if pattern == '':
            return True

        pattern = '*{}*'.format(pattern)

        model = self.sourceModel()
        result = False
        index = model.index(row, self.filter_column, parent)
        self_index = self.index(row, self.filter_column, parent)
        result |= self.hasChildren(self_index)
        self.wildcard.setPattern(pattern)
        result |= self.wildcard.exactMatch(model.data(index, QtCore.Qt.DisplayRole))

        return result

    def next_row(self, index):
        return self.sibling(
            index.row() + 1,
            index.column(),
            index,
        )

    def next_index(self, index, allow_children=True):
        if allow_children and self.hasChildren(index):
            return self.index(0, index.column(), index), False

        next_ = self.next_row(index)
        if not next_.isValid():
            while True:
                index = index.parent()
                if not index.isValid():
                    return self.index(0, 0, QtCore.QModelIndex()), True

                next_ = self.next_row(index)
                if next_.isValid():
                    break

        return next_, False

    def search(self, text, search_from, column):
        def set_row_column(index, row=None, column=None):
            if row is None:
                row = index.row()

            if column is None:
                column = index.column()

            return self.index(
                row,
                column,
                index.parent(),
            )

        if text == '':
            return None

        text = '*{}*'.format(text)

        flags = (
            QtCore.Qt.MatchContains
            | QtCore.Qt.MatchRecursive
            | QtCore.Qt.MatchWildcard
        )

        wrapped = False

        if search_from.isValid():
            search_from, wrapped = self.next_index(search_from)
        else:
            search_from = self.index(0, 0, QtCore.QModelIndex())

        while True:
            next_indexes = self.match(
                set_row_column(index=search_from, column=column),
                QtCore.Qt.DisplayRole,
                text,
                1,
                flags,
            )

            if len(next_indexes) > 0:
                next_index, = next_indexes

                if not next_index.isValid():
                    break

                return next_index
            elif wrapped:
                break

            search_from, wrapped = self.next_index(search_from)

        # TODO: report not found and/or wrap
        print('reached end')
        return None


def load_ui(filepath, base_instance):
    # TODO: CAMPid 9549757292917394095482739548437597676742
    ui_file = QtCore.QFile(filepath)
    ui_file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
    ts = QtCore.QTextStream(ui_file)
    sio = io.StringIO(ts.readAll())

    return PyQt5.uic.loadUi(sio, base_instance)


def search_view(view, text, column):
    model = view.model()

    if text == '':
        return

    index = model.search(
        text=text,
        column=column,
        search_from=view.currentIndex(),
    )

    if index is not None:
        parent = index.parent()
        # TODO: not sure why but this must be set to zero or the row
        #       won't be highlighted.  it still gets expanded and printing
        #       the display role data still works.
        parent = model.index(parent.row(), 0, parent.parent())
        index = model.index(index.row(), index.column(), parent)
        view.setCurrentIndex(index)
