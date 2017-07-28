import functools
import io
import os
import sys
import textwrap
import time
import traceback

import epyqlib.utils.general

from PyQt5 import QtCore, QtWidgets, QtGui

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 953295425421677545429542967596754
log = os.path.join(os.getcwd(), 'epyq.log')


_version_tag = None
_build_tag = None


def exception_message_box_register_versions(version_tag, build_tag):
    global _version_tag
    global _build_tag

    _version_tag = version_tag
    _build_tag = build_tag


def exception_message_box(excType=None, excValue=None, tracebackobj=None,
                          parent=None):
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
        parent=parent,
    )


def custom_exception_message_box(brief, extended='', parent=None, stderr=True):
    email = "kyle.altendorf@epcpower.com"

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

    notice = textwrap.dedent('''\
        An unhandled exception occurred. Please report the problem via email to:
                        {email}

        {brief}

        {info}A log has been written to "{log}".
        {time_string}''')

    complete = notice.format(
        email=email,
        info=info,
        log=log,
        time_string=time_string,
        brief=brief,
        extended=extended,
    )

    if len(extended) > 0:
        complete = '\n'.join(s.strip() for s in (complete, '-' * 70, extended))

    if stderr:
        sys.stderr.write(complete + '\n')

    dialog(
        parent=parent,
        title='Exception',
        message=complete,
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
        self.copy = QtWidgets.QPushButton(parent)
        self.buttons = QtWidgets.QDialogButtonBox(parent)

        self.copy.setText('Copy To Clipboard')

        self.layout.addWidget(self.icon, 0, 0)
        self.layout.addWidget(self.message, 0, 1, 1, 2)
        self.layout.addWidget(self.copy, 1, 1)
        self.layout.addWidget(self.buttons, 1, 2)

        self.layout.setAlignment(self.copy, QtCore.Qt.AlignLeft)

        self.layout.setRowStretch(0, 1)
        self.layout.setColumnStretch(1, 1)


class Dialog(QtWidgets.QDialog):
    def __init__(self, *args, cancellable=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = DialogUi(parent=self)

        self.ui.buttons.accepted.connect(self.accept)
        self.ui.buttons.rejected.connect(self.reject)

        self.ui.copy.clicked.connect(self.copy)

        self.setLayout(self.ui.layout)
        buttons = QtWidgets.QDialogButtonBox.Ok
        if cancellable:
            buttons |= QtWidgets.QDialogButtonBox.Cancel

        self.ui.buttons.setStandardButtons(buttons)

        self.text = None
        self.html = None

        self.cached_maximum_size = self.maximumSize()

        desktops = QtWidgets.QApplication.desktop()
        screen_number = desktops.screenNumber(self.parent())
        geometry = desktops.screenGeometry(screen_number)

        self.setMaximumHeight(geometry.height() * 0.7)
        self.setMaximumWidth(geometry.width() * 0.7)

    def copy(self):
        QtWidgets.QApplication.clipboard().setText(
            self.ui.message.toPlainText() + '\n'
        )

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

    def set_message_box_icon(self, icon):
        self.ui.icon.setPixmap(QtWidgets.QMessageBox.standardIcon(icon))

    def exec(self):
        QtCore.QTimer.singleShot(10, functools.partial(
                self.setMaximumSize,
                self.cached_maximum_size,
        ))

        return super().exec()


def dialog(parent, message, title=None, icon=None,
           rich_text=False, cancellable=False):
    box = Dialog(parent=parent, cancellable=cancellable)

    if rich_text:
        box.set_html(message)
    else:
        box.set_text(message)

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
