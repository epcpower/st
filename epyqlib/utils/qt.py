import functools
import io
import os
import sys
import time
import traceback

import epyqlib.utils.general

from PyQt5 import QtCore, QtWidgets, QtGui

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 953295425421677545429542967596754
log = os.path.join(os.getcwd(), 'epyq.log')

# TODO: Consider updating from...
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/eric6.py#l134

def exception_message_box(excType=None, excValue=None, tracebackobj=None, *,
                          message=None, version_tag=None, parent=None):
    """
    Global function to catch unhandled exceptions.

    @param excType exception type
    @param excValue exception value
    @param tracebackobj traceback object
    """
    separator = '-' * 70
    email = "kyle.altendorf@epcpower.com"

    if version_tag is not None:
        version = '\n\nVersion Tag: {}\n\n'.format(version_tag)
    else:
        version = ''

    notice = \
        """An unhandled exception occurred. Please report the problem via email to:\n"""\
        """\t\t{email}{version}"""\
        """A log has been written to "{log}".\n\nError information:\n""".format(
        email=email, version=version, log=log)
    # TODO: add something for version
    versionInfo=""
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

    if message is None:
        tbinfo = ''.join(traceback.format_tb(tracebackobj))
        errmsg = ''.join(traceback.format_exception_only(excType, excValue))
        sections = [separator, timeString, separator, errmsg, separator, tbinfo]
        message = '\n'.join(s.strip() for s in sections)

    complete = str(notice) + str(message) + str(versionInfo)

    sys.stderr.write(complete + '\n')

    dialog(
        parent=parent,
        title='EPyQ Exception',
        message=complete,
        scrollable=True,
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


def file_dialog(filters, default=0, save=False, parent=None):
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
        code = code.decode('utf-8').strip().encode('ascii')
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


def dialog(parent, title, message, scrollable=False, icon=None):
    post_show = None

    if not scrollable:
        box = QtWidgets.QMessageBox(parent=parent)
        box.setText(message)
        if icon is not None:
            box.setIcon(icon)
    else:
        box = QtWidgets.QInputDialog(parent=parent)
        box.setOptions(QtWidgets.QInputDialog.UsePlainTextEditForTextInput)
        box.setTextValue(message)
        box.setLabelText('')

        text_edit = box.findChildren(QtWidgets.QPlainTextEdit)[0]

        metric = text_edit.fontMetrics()
        line_widths = sorted([metric.width(line) for line
                              in message.splitlines()])

        index = int(0.95 * len(line_widths))
        width = line_widths[index]

        desktops = QtWidgets.QApplication.desktop()
        screen_number = desktops.screenNumber(parent)
        geometry = desktops.screenGeometry(screen_number)

        width = min(width * 1.1, geometry.width() * 0.7)

        text_edit.setReadOnly(True)

        default_width = box.minimumWidth()
        default_height = box.minimumHeight()

        number_of_lines = message.count('\n') + 1
        height = number_of_lines * metric.lineSpacing()
        height = min(height * 1.1, geometry.height() * 0.7)

        def post_show():
            text_edit.moveCursor(QtGui.QTextCursor.Start)
            text_edit.setMinimumWidth(width)
            text_edit.setMinimumHeight(height)

            def g():
                text_edit.setMinimumWidth(default_width)
                text_edit.setMinimumHeight(default_height)

            QtCore.QTimer.singleShot(100, g)

        if icon is not None:
            horizontal_layout = QtWidgets.QHBoxLayout()
            vertical_layout = text_edit.parent().layout()
            vertical_layout.insertLayout(0, horizontal_layout)

            vertical_layout.removeWidget(text_edit)
            pixmap = QtWidgets.QMessageBox.standardIcon(icon)
            label = QtWidgets.QLabel()
            label.setPixmap(pixmap)
            horizontal_layout.addWidget(label)
            horizontal_layout.addWidget(text_edit)

    box.setWindowTitle(title)

    if post_show is not None:
        QtCore.QTimer.singleShot(100, post_show)

    box.exec_()


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
        scrollable=True,
    )
