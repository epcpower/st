#!/usr/bin/env python3

# TODO: get some docstrings in here!

# TODO: CAMPid 98852142341263132467998754961432
import epyqlib.tee
import os
import pathlib
import sys

from epyqlib.tabs.files.aws_login_manager import AwsLoginManager
from epyqlib.tabs.files.sync_config import SyncConfig, Vars

# TODO: CAMPid 953295425421677545429542967596754
log = open(os.path.join(os.getcwd(), "epyq.log"), "w", encoding="utf-8", buffering=1)

if sys.stdout is None:
    sys.stdout = log
else:
    sys.stdout = epyqlib.tee.Tee([sys.stdout, log])

if sys.stderr is None:
    sys.stderr = log
else:
    sys.stderr = epyqlib.tee.Tee([sys.stderr, log])

import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")

import attr
import epyq
import epyqlib.canneo
import epyqlib.csvwindow
import epyqlib.scripting
import epyqlib.scriptingview
import epyqlib.tests.common
import epyqlib.txrx
import epyqlib.utils.qt
import epyqlib.utils.canlog
import epyqlib.widgets.progressbar
import epyqlib.widgets.lcd
import epyqlib.widgets.led
import functools
import io
import signal

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import QFile, QFileInfo, QTextStream, Qt, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMessageBox, QAction

import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()

import epyq.main_ui
import epyqlib.utils.qt

# See file COPYING in this source tree
__copyright__ = "Copyright 2017, EPC Power Corp."
__license__ = "GPLv2+"


print(epyq.__version_tag__)
print(epyq.__build_tag__)


# TODO: CAMPid 9756562638416716254289247326327819
class Window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.aws_login_manager = AwsLoginManager.get_instance()
        self.aws_login_manager.register_listener(self.update_logged_in_state)
        self.files_config = SyncConfig.get_instance()

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), "icon.ico")
        ico = QtGui.QIcon(ico_file)
        self.setWindowIcon(ico)

        self.ui = epyq.main_ui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.action_about.triggered.connect(self.about_dialog)
        self.ui.action_license.triggered.connect(self.license_dialog)
        self.ui.action_third_party_licenses.triggered.connect(
            self.third_party_licenses_dialog
        )

        self.ui.action_chart_log.triggered.connect(self.chart_log)

        self.ui.action_scripting.triggered.connect(self.scripting)

        self.ui.action_start_can_log.triggered.connect(self.start_can_log)
        self.ui.action_stop_can_log.triggered.connect(self.stop_can_log)
        self.ui.action_export_can_log.triggered.connect(self.export_can_log)
        self.can_logs = {}

        self.ui.action_login_to_sync.triggered.connect(self.login_to_sync_clicked)
        self.ui.action_auto_sync_files.triggered.connect(self.auto_sync_clicked)
        self.update_logged_in_state()

        device_tree = epyqlib.devicetree.Tree()
        self.device_tree_model = epyqlib.devicetree.Model(root=device_tree)
        self.device_tree_model.device_removed.connect(self._remove_device)
        self.ui.device_tree.setModel(self.device_tree_model)
        self.ui.device_tree.device_selected.connect(self.set_current_device)

        self.ui.collapse_button.clicked.connect(self.collapse_expand)
        size_hint = self.ui.collapse_button.sizeHint()
        size_hint.setWidth(0.75 * size_hint.width())
        size_hint.setHeight(6 * size_hint.width())
        self.ui.collapse_button.setMinimumSize(size_hint)
        self.ui.collapse_button.setMaximumSize(size_hint)

        self.subwindows = set()

        self.set_title()

        self.ui.stacked.currentChanged.connect(self.device_widget_changed)
        self.ui.device_tree.model.details_changed.connect(
            self.device_widget_changed,
        )

        self.scripting_window = None

    def start_can_log(self):
        self.stop_can_log()

        self.can_logs = {}
        for bus in self.device_tree_model.root.children:
            if bus.interface is not None:
                name = bus.fields.name
                log = epyqlib.utils.canlog.Log(name=name)
                bus.bus.notifier.add(log)
                bus.bus.tx_notifier.add(log)
                self.can_logs[bus.bus] = log

                log.start()

    def stop_can_log(self):
        for bus, log in self.can_logs.items():
            log.stop()
            bus.notifier.discard(log)

    def export_can_log(self):
        nonempty_logs = {
            bus: log for bus, log in self.can_logs.items() if len(log.messages) > 0
        }

        if len(nonempty_logs) == 0:
            # TODO: notify user that nothing will be done
            return

        first_message_time = min(
            log.minimum_timestamp()
            for log in nonempty_logs.values()
            if len(log.messages) > 0
        )

        for bus, log in nonempty_logs.items():
            if len(log.messages) > 0:
                QMessageBox.information(
                    self,
                    "EPyQ",
                    "Pick a file to save log of '{}'".format(log.name),
                )

                filters = [("PCAN", ["trc"]), ("All Files", ["*"])]
                filename = epyqlib.utils.qt.file_dialog(
                    filters=filters,
                    parent=self,
                    save=True,
                )

                if filename is not None:
                    messages = (
                        attr.evolve(
                            message,
                            time=(
                                message.time - first_message_time
                                if message.time is not None
                                else 0
                            ),
                            type=(
                                epyqlib.utils.canlog.MessageType.Rx
                                if message.time is not None
                                else epyqlib.utils.canlog.MessageType.Tx
                            ),
                        )
                        for message in log.messages
                    )
                    with open(filename, "w") as f:
                        epyqlib.utils.canlog.to_trc_v1_1(messages, f)

    def update_logged_in_state(self, logged_in: bool = None):
        if logged_in is None:
            logged_in = self.aws_login_manager.is_logged_in()

        auto_sync: QAction = self.ui.action_auto_sync_files
        login: QAction = self.ui.action_login_to_sync

        if logged_in:
            text = "Log out of EPC Sync"
        else:
            text = "Log in to EPC Sync"

        login.setText(text)
        auto_sync.setDisabled(not logged_in)
        auto_sync.setChecked(logged_in and self.files_config.get_bool(Vars.auto_sync))

    def login_to_sync_clicked(self):
        if self.aws_login_manager.is_logged_in():
            self.aws_login_manager.log_user_out()
        else:
            self.aws_login_manager.show_login_window()

    def auto_sync_clicked(self):
        auto_sync: QAction = self.ui.action_auto_sync_files

        self.files_config.set(Vars.auto_sync, auto_sync.isChecked())

    def device_widget_changed(self, index=None):
        if index is not None:
            device = self.device_tree_model.device_from_widget(
                widget=self.ui.stacked.widget(index)
            )
        else:
            device = self.device_tree_model.device_from_widget(
                widget=self.ui.stacked.currentWidget()
            )

        details = []
        if device is not None:
            if len(device.nickname) > 0:
                details.append(device.nickname)
            details.append(device.name)

        self.set_title(detail=" - ".join(details))

    def set_title(self, detail=None, window=None):
        if window is None:
            window = self

        title = "EPyQ v{}".format(epyq.__version__)

        if detail is not None:
            title = " - ".join((title, detail))

        window.setWindowTitle(title)

    def closeEvent(self, event):
        self.device_tree_model.terminate()
        if self.scripting_window is not None:
            self.scripting_window.close()

    def collapse_expand(self):
        self.ui.device_tree.setVisible(not self.ui.device_tree.isVisible())
        self.ui.collapse_button.setArrowType(
            Qt.LeftArrow if self.ui.device_tree.isVisible() else Qt.RightArrow
        )

    def license_dialog(self):
        epyqlib.utils.qt.dialog_from_file(
            parent=self,
            title="EPyQ License",
            file_name="epyq-COPYING.txt",
        )

    def third_party_licenses_dialog(self):
        epyqlib.utils.qt.dialog_from_file(
            parent=self,
            title="Third Party Licenses",
            file_name="third_party-LICENSE.txt",
        )

    def about_dialog(self):
        message = [
            __copyright__,
            __license__,
            "Version Tag: {}".format(epyq.__version_tag__),
            "Build Tag: {}".format(epyq.__build_tag__),
        ]

        message = "\n".join(message)

        epyqlib.utils.qt.dialog(
            parent=self,
            title="About EPyQ",
            message=message,
        )

    def chart_log(self):
        filters = [("CSV", ["csv"]), ("All Files", ["*"])]
        filename = epyqlib.utils.qt.file_dialog(filters, parent=self)

        if filename is not None:
            filename = pathlib.Path(filename)
            data = epyqlib.csvwindow.read_csv(filename)
            window = epyqlib.csvwindow.QtChartWindow(data=data)
            self.set_title(detail=filename.name, window=window)
            self.subwindows.add(window)
            window.closing.connect(functools.partial(self.subwindows.discard, window))
            window.show()

    def scripting(self):
        if self.scripting_window is not None:
            self.scripting_window.raise_()
            return

        self.scripting_window = epyqlib.scriptingview.ScriptingView()
        scripting_model = epyqlib.scripting.Model(
            get_devices=lambda: {
                device.device.nickname: device.device
                for device in self.device_tree_model.root.nodes_by_filter(
                    filter=lambda node: isinstance(
                        node,
                        epyqlib.devicetree.Device,
                    ),
                )
                if len(device.device.nickname) > 0
            }
        )
        self.scripting_window.set_model(scripting_model)
        self.scripting_window.closing.connect(self.scripting_closing)
        self.set_title(detail="Scripting", window=self.scripting_window)
        self.scripting_window.show()

    def scripting_closing(self):
        self.scripting_window = None

    @pyqtSlot(object)
    def _remove_device(self, device):
        self.ui.stacked.removeWidget(device.ui)
        device.ui.setParent(None)
        device.terminate()

    @pyqtSlot(object)
    def set_current_device(self, device):
        self.ui.stacked.addWidget(device.ui)
        self.ui.stacked.setCurrentWidget(device.ui)


def sigint_handler(signal_number, stack_frame):
    QApplication.exit(128 + signal_number)


def main(args=None):
    print("starting epyq")

    signal.signal(signal.SIGINT, sigint_handler)

    # TODO: CAMPid 9757656124812312388543272342377
    app = QApplication(sys.argv)
    epyqlib.utils.qt.exception_message_box_register_versions(
        version_tag=epyq.__version_tag__,
        build_tag=epyq.__build_tag__,
    )
    sys.excepthook = functools.partial(
        epyqlib.utils.qt.exception_message_box,
    )
    QtCore.qInstallMessageHandler(epyqlib.utils.qt.message_handler)
    app.setStyleSheet(
        "QMessageBox {{ messagebox-text-interaction-flags: {}; }}".format(
            Qt.TextBrowserInteraction
        )
    )
    app.setOrganizationName("EPC Power Corp.")
    app.setApplicationName("EPyQ")

    os_signal_timer = QtCore.QTimer()
    os_signal_timer.start(200)
    os_signal_timer.timeout.connect(lambda: None)

    # TODO: CAMPid 03127876954165421679215396954697
    # https://github.com/kivy/kivy/issues/4182#issuecomment-253159955
    # fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
    if "twisted.internet.reactor" in sys.modules:
        del sys.modules["twisted.internet.reactor"]

    import qt5reactor

    qt5reactor.install()

    import argparse

    ui_default = "main.ui"

    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--quit-after", type=float, default=None)
    parser.add_argument("--load-offline", default=None)
    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)

    can_logger_modules = ("can", "can.socketcan.native")

    for module in can_logger_modules:
        logging.getLogger(module).setLevel(logging.WARNING)

    if args.verbose >= 1:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

    if args.verbose >= 2:
        import twisted.internet.defer

        twisted.internet.defer.setDebugging(True)

    if args.verbose >= 3:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.verbose >= 4:
        logging.getLogger().setLevel(logging.INFO)
        for module in can_logger_modules:
            logging.getLogger(module).setLevel(logging.DEBUG)

    window = Window()
    epyqlib.utils.qt.exception_message_box_register_parent(parent=window)

    window.show()

    if args.quit_after is not None:
        QtCore.QTimer.singleShot(args.quit_after * 1000, app.quit)

    if args.load_offline is not None:

        def load_offline():
            (bus_node,) = [
                node
                for node in window.ui.device_tree.model.root.children
                if node.fields.name == "Offline"
            ]

            split = args.load_offline.split("_", maxsplit=1)
            if split[0] == "test":
                path = epyqlib.tests.common.devices[split[1]]
            else:
                path = args.load_offline

            window.ui.device_tree.add_device(
                bus=bus_node,
                device=epyqlib.device.Device(
                    file=path,
                    bus=bus_node.bus,
                    node_id=247,
                ),
            )

        QtCore.QTimer.singleShot(0.5 * 1000, load_offline)

    from twisted.internet import reactor

    reactor.runReturn()
    result = app.exec()
    if reactor.threadpool is not None:
        reactor._stopThreadPool()
        logging.debug("Thread pool stopped")
    logging.debug("Application ended")
    reactor.stop()
    logging.debug("Reactor stopped")

    # TODO: this should be sys.exit() but something keeps the process
    #       from terminating.  Ref T679  Ref T711
    os._exit(result)


if __name__ == "__main__":
    sys.exit(main())
