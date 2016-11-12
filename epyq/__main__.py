#!/usr/bin/env python3

# TODO: get some docstrings in here!

# TODO: CAMPid 98852142341263132467998754961432
import epyqlib.tee
import os
import sys

log = open(os.path.join(os.getcwd(), 'epyq.log'), 'w', encoding='utf-8', buffering=1)

if sys.stdout is None:
    sys.stdout = log
else:
    sys.stdout = epyqlib.tee.Tee([sys.stdout, log])

if sys.stderr is None:
    sys.stderr = log
else:
    sys.stderr = epyqlib.tee.Tee([sys.stderr, log])

try:
    import epyq.revision
except ImportError:
    pass
else:
    print(epyq.revision.hash)

import can
import copy
import epyqlib.canneo
import epyqlib.nv
from epyqlib.svgwidget import SvgWidget
import epyqlib.txrx
import epyqlib.widgets.progressbar
import epyqlib.widgets.lcd
import epyqlib.widgets.led
import functools
import io
import math
import platform

from epyqlib.device import Device

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                          Qt, pyqtSlot, QMarginsF)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QLabel,
                             QListWidgetItem, QAction, QMenu, QInputDialog,
                             QPlainTextEdit)
from PyQt5.QtGui import QPixmap, QPicture, QTextCursor
import qt5reactor
import time
import traceback
import twisted

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 9756562638416716254289247326327819
class Window(QtWidgets.QMainWindow):
    def __init__(self, ui_file, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        self.setWindowIcon(ico)

        ui = ui_file
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

        self.ui.action_about.triggered.connect(self.about_dialog)
        self.ui.action_license.triggered.connect(self.license_dialog)
        self.ui.action_third_party_licenses.triggered.connect(
            self.third_party_licenses_dialog)

        device_tree = epyqlib.devicetree.Tree()
        device_tree_model = epyqlib.devicetree.Model(root=device_tree)
        device_tree_model.device_removed.connect(self._remove_device)
        self.ui.device_tree.setModel(device_tree_model)

        self.ui.device_tree.device_selected.connect(self.set_current_device)

    def dialog_from_file(self, title, file_name):
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

        self.dialog(title=title,
                    message=message,
                    scrollable=True)

    def license_dialog(self):
        self.dialog_from_file(title='EPyQ License',
                              file_name='epyq-COPYING.txt')

    def third_party_licenses_dialog(self):
        self.dialog_from_file(title='Third Party Licenses',
                              file_name='third_party-LICENSE.txt')

    def about_dialog(self):
        message = [
            __copyright__,
            __license__
        ]

        try:
            import epyq.revision
        except ImportError:
            pass
        else:
            message.append(epyq.revision.hash)

        message = '\n'.join(message)

        self.dialog(title='About EPyQ',
                    message=message)

    def dialog(self, title, message, scrollable=False):
        if not scrollable:
            box = QMessageBox()
            box.setText(message)
        else:
            box = QInputDialog()
            box.setOptions(QInputDialog.UsePlainTextEditForTextInput)
            box.setTextValue(message)
            box.setLabelText('')

            text_edit = box.findChildren(QPlainTextEdit)[0]

            metric = text_edit.fontMetrics()
            line_widths = sorted([metric.width(line) for line
                                  in message.splitlines()])

            index = int(0.95 * len(line_widths))
            width = line_widths[index]

            text_edit.setMinimumWidth(width * 1.1)
            text_edit.setReadOnly(True)

        box.setWindowTitle(title)

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)),
                                'icon.ico')
        ico = QtGui.QIcon(ico_file)
        box.setWindowIcon(ico)

        box.exec_()

    @pyqtSlot(epyqlib.device.Device)
    def _remove_device(self, device):
        self.ui.stacked.removeWidget(device.ui)

    @pyqtSlot(epyqlib.device.Device)
    def set_current_device(self, device):
        self.ui.stacked.addWidget(device.ui)
        self.ui.stacked.setCurrentWidget(device.ui)


# TODO: Consider updating from...
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/eric6.py#l134

# TODO: deal with licensing for swiped code (GPL3)
#       http://die-offenbachs.homelinux.org:48888/hg/eric/file/a1e53a9ffcf3/LICENSE.GPL3

def excepthook(excType, excValue, tracebackobj):
    """
    Global function to catch unhandled exceptions.

    @param excType exception type
    @param excValue exception value
    @param tracebackobj traceback object
    """
    separator = '-' * 70
    email = "kyle.altendorf@epcpower.com"

    try:
        hash = 'Revision Hash: {}\n\n'.format(epyq.revision.hash)
    except:
        hash = ''

    notice = \
        """An unhandled exception occurred. Please report the problem via email to:\n"""\
        """\t\t{email}\n\n{hash}"""\
        """A log has been written to "{log}".\n\nError information:\n""".format(
        email=email, hash=hash, log=log.name)
    # TODO: add something for version
    versionInfo=""
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

    tbinfofile = io.StringIO()
    traceback.print_tb(tracebackobj, None, tbinfofile)
    tbinfofile.seek(0)
    tbinfo = tbinfofile.read()
    errmsg = '%s: \n%s' % (str(excType), str(excValue))
    sections = [separator, timeString, separator, errmsg, separator, tbinfo]
    msg = '\n'.join(sections)

    errorbox = QMessageBox()
    errorbox.setWindowTitle("EPyQ")
    errorbox.setIcon(QMessageBox.Critical)

    # TODO: CAMPid 980567566238416124867857834291346779
    ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
    ico = QtGui.QIcon(ico_file)
    errorbox.setWindowIcon(ico)

    complete = str(notice) + str(msg) + str(versionInfo)

    sys.stderr.write(complete)
    errorbox.setText(complete)
    errorbox.exec_()


def main(args=None):
    print('starting epyq')

    # TODO: CAMPid 9757656124812312388543272342377
    app = QApplication(sys.argv)
    sys.excepthook = excepthook
    app.setStyleSheet('QMessageBox {{ messagebox-text-interaction-flags: {}; }}'
                      .format(Qt.TextBrowserInteraction))
    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPyQ')

    qt5reactor.install()

    if args is None:
        import argparse

        ui_default = 'main.ui'

        parser = argparse.ArgumentParser()
        parser.add_argument('--ui', default=ui_default)
        args = parser.parse_args()

    window = Window(ui_file=args.ui)

    window.show()
    from twisted.internet import reactor
    reactor.runReturn()
    app.aboutToQuit.connect(reactor.stop)
    result = app.exec_()
    return result


if __name__ == '__main__':
    sys.exit(main())
