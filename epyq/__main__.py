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
    revision_hash = None
else:
    revision_hash = epyq.revision.hash
    print(revision_hash)

import can
import canmatrix.importany as importany
import copy
import epyqlib.widgets.abstractwidget
import epyqlib.busproxy
import epyqlib.canneo
import epyqlib.device
import epyqlib.hmidialog
import epyqlib.listmenuview
import epyqlib.listselect
import epyqlib.numberpad
import epyqlib.nv
import epyqlib.parameteredit
import epyqlib.stylesheets

from epyqlib.svgwidget import SvgWidget
import epyqlib.txrx
import epyqlib.wehmd
import functools
import io
import math
import platform
import socket
import subprocess
import textwrap
# TODO: This is negative on the embedded side
#       http://bugs.python.org/issue28215
try:
    socket.CAN_EFF_FLAG = abs(socket.CAN_EFF_FLAG)
except AttributeError:
    # If it's not there, then it doesn't need to be corrected.
    pass

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import (QFile, QFileInfo, QTextStream, QCoreApplication,
                          QSettings, Qt, pyqtSlot, QMarginsF, QTextCodec,
                          QObject, QEvent, pyqtProperty, QTimer)
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QLabel,
                             QListWidgetItem, QAction, QMenu, QFrame,
                             QAbstractScrollArea, QWidget, QPushButton)
from PyQt5.QtGui import (QPixmap, QPicture, QFont, QFontDatabase, QMouseEvent,
                         QIcon)
import time
import traceback

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def load_ui(filename):
    # TODO: CAMPid 9549757292917394095482739548437597676742
    if not QFileInfo(filename).isAbsolute():
        ui_file = os.path.join(
            QFileInfo.absolutePath(QFileInfo(__file__)), filename)
    else:
        ui_file = filename
    ui_file = QFile(ui_file)
    ui_file.open(QFile.ReadOnly | QFile.Text)
    ts = QTextStream(ui_file)
    sio = io.StringIO(ts.readAll())
    return uic.loadUi(sio)


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class StackedManager:
    def __init__(self, stacked, menu_model, menu_view, number_pad,
                 list_select, bus, length=20):
        self.bus = bus
        self.list_select = list_select
        # TODO: probably ought to only have either the view or the model...
        self.menu_model = menu_model
        self.menu_view = menu_view
        self.number_pad = number_pad
        self.stacked_widget = stacked
        self.length = length

        self.stacked_widget.currentChanged.connect(self.changed)

        self.history = []

        self.add(self.number_pad)

    def changed(self, index):
        self.history.append(index)
        self.history = self.history[-self.length:]

    def focus_previous(self, steps=1):
        self.stacked_widget.setCurrentIndex(self.history[-(steps+1)])

    def add(self, widget):
        self.stacked_widget.addWidget(widget)
        widget.setProperty('is_stacked_widget', True)

    def set_widget_value(self, dash, widget, value):
        if value is not None:
            widget.user_set_value(value)
        self.stacked_widget.setCurrentWidget(dash)

    def trigger_numberpad(self, dash, widget):
        number_pad.focus(value=widget.signal_object.get_human_value(),
                         action=functools.partial(
                             self.set_widget_value, widget=widget, dash=dash),
                         label='{} [{}]'.format(widget.ui.label.text(),
                                                widget.ui.units.text()))

    def connect_to_numberpad(self, dash, widget, signal):
        signal.connect(functools.partial(
            self.number_pad.focus,
            value=widget.signal_object.get_human_value(),
            action=functools.partial(
                self.set_widget_value, widget=widget, dash=dash),
            label='{} [{}]'.format(widget.ui.label.text(),
                                   widget.ui.units.text())
        ))

    def set_widget_value_from_list(self, dash, widget, value):
        if value is not None:
            widget.user_set_value(value)
        self.stacked_widget.setCurrentWidget(dash)

    def trigger_list_menu(self, dash, widget):
        signal = widget.signal_object
        items = {key: value
                 for key, value in signal.enumeration.items()
                 if signal.min <= key <= signal.max}

        self.list_select.focus(value=widget.signal_object.get_human_value(),
                               action=functools.partial(
                                   self.set_widget_value_from_list,
                                   widget=widget,
                                   dash=dash),
                               items=items,
                               label='{}'.format(widget.ui.label.text()))

    def connect_to_list_menu(self, dash, widget, signal):
        signal.connect(functools.partial(
            self.trigger_list_menu,
            dash=dash,
            widget=widget
        ))

    def to_menu(self, auto_level_up=True, check=False):
        if check:
            return self.menu_view == self.stacked_widget.currentWidget()

        self.bus.set_filters([])

        if (self.menu_view == self.stacked_widget.currentWidget()
                and auto_level_up):
            self.menu_view.ui.esc_button.clicked.emit()
        else:
            self.stacked_widget.setCurrentWidget(self.menu_view)

    def focus_dash(self, dash, check=False):
        if check:
            return self.stacked_widget.currentWidget() == dash

        filters = []
        if platform.system() != 'Windows':
            filters.extend([
                               {
                                   'can_id': frame.id | socket.CAN_EFF_FLAG,
                                   'can_mask': socket.CAN_EFF_MASK |
                                               socket.CAN_EFF_FLAG |
                                               socket.CAN_RTR_FLAG
                               }
                               for frame in dash.connected_frames
                               ])

            self.bus.set_filters(filters)

        self.stacked_widget.setCurrentWidget(dash)

    def focus_menu_node(self, node=None, check=False):
        if check:
            return (self.stacked_widget.currentWidget() == self.menu_view
                    and node == self.menu_model.root)

        self.to_menu(auto_level_up=False)
        if node not in [None, self.menu_model.root]:
            self.menu_model.node_clicked(node)


class Playback:
    def __init__(self, bus):
        self.bus = bus
        self.process = None

    def toggle(self, check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        if self.process is None:
            real_bus = can.interface.Bus(bustype='socketcan',
                                         channel='vcan0',
                                         can_filters=[])
            self.bus.set_bus(bus=real_bus)

            dump = '/opt/st.hmi/demo.candump'
            if not os.path.isfile(dump):
                dump = os.path.join(os.path.dirname(__file__),
                                    '..', 'demo.candump')

            self.process = subprocess.Popen(
                ['/usr/bin/canplayer', '-I', dump, '-l', 'i', 'vcan0=can0'],
            )
        else:
            self.process.terminate()
            self.process = None

            real_bus = can.interface.Bus(bustype='socketcan',
                                         channel='can0',
                                         can_filters=[])
            self.bus.set_bus(bus=real_bus)


class ShortcutButton(QPushButton):
    def __init__(self, icon, reference_directory, *args, **kwargs):
        QPushButton.__init__(self, *args, **kwargs)
        self.target_widget = None
        self._active = False
        self.active = False
        self.action = None

        if os.path.splitext(icon)[1] in ['.svg', '.png']:
            self.setIcon(QIcon(os.path.join(reference_directory, icon)))
        else:
            base = 16 if icon.startswith('0x') else 10
            character = chr(int(icon, base))
            self.setText(character)

        self.setFont(QFont('FontAwesome'))

        self.clicked.connect(self.trigger_action)

    def trigger_action(self):
        self.action()

    @pyqtProperty(bool)
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        active = bool(active)

        if self._active != active:
            self._active = active
            self.setProperty('active', self.active)
            repolish(self)

    def active_widget_changed(self, index):
        self.active = self.action(check=True)


class TooltipEventFilter(QObject):
    def __init__(self, dialog, history, parent=None, trigger_widget=None):
        QObject.__init__(self, parent)
        self.dialog = dialog
        self.history = history
        self.trigger_widget = trigger_widget

    def deactivate(self):
        self.parent().removeEventFilter(self)
        self.trigger_widget.setProperty('active', False)
        repolish(self.trigger_widget)

    def action(self, check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        if self.trigger_widget.property('active'):
            self.deactivate()
        else:
            self.trigger_widget.setProperty('active', True)
            repolish(self.trigger_widget)
            self.parent().installEventFilter(self)

    def eventFilter(self, object, event):
        if (isinstance(event, QMouseEvent)
            and event.button() == Qt.LeftButton
            and event.type() == QEvent.MouseButtonRelease):
            self.deactivate()

            widget = self.parent().widgetAt(event.globalPos())
            while not isinstance(
                    widget, epyqlib.widgets.abstractwidget.AbstractWidget):
                if widget is None:
                    break
                widget = widget.parent()
            else:
                self.dialog.focus(
                    ok_action=self.history.focus_previous,
                    label=widget.toolTip(),
                    enable_delay=0
                )

            return True

        return False


class Screensaver(QObject):
    def __init__(self, application, parent, pixmap, timeout=60):
        QObject.__init__(self, parent)

        application.installEventFilter(self)

        self.shown = False

        self.overlay = epyqlib.overlaylabel.OverlayLabel(parent=parent)
        self.overlay.label.setText('')
        self.overlay.setVisible(False)

        self.overlay.label.setPixmap(pixmap)

        self.timer = QTimer()
        self.timer.setInterval(timeout * 1000)
        self.timer.timeout.connect(self.show)
        self.timer.start()

    def eventFilter(self, object, event):
        if (isinstance(event, QMouseEvent)
            and event.button() == Qt.LeftButton
            and event.type() == QEvent.MouseButtonRelease):
            self.timer.stop()
            self.timer.start()

            if self.shown:
                self.shown = False
                self.overlay.setVisible(False)

                return True

        return False

    def show(self):
        self.shown = True
        self.overlay.setVisible(True)


class ActionClickHandler(QObject):
    def __init__(self, action, parent=None):
        QObject.__init__(self, parent)

        self.action = action

    def eventFilter(self, qobject, qevent):
        if isinstance(qevent, QMouseEvent):
            if (qevent.button() == Qt.LeftButton
                and qevent.type() == QEvent.MouseButtonRelease
                and qobject.rect().contains(qevent.localPos().toPoint())):
                self.action()

            return True

        return False


embedded = os.environ.get('QT_QPA_PLATFORM') == 'linuxfb'


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

    hash = 'Revision Hash: {}\n\n'.format(revision_hash)

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

    complete = str(notice) + str(msg) + str(versionInfo)

    sys.stderr.write(complete)

    if not embedded:
        errorbox = QMessageBox()
        errorbox.setWindowTitle("EPyQ")
        errorbox.setIcon(QMessageBox.Critical)

        # TODO: CAMPid 980567566238416124867857834291346779
        ico_file = os.path.join(QFileInfo.absolutePath(QFileInfo(__file__)), 'icon.ico')
        ico = QtGui.QIcon(ico_file)
        errorbox.setWindowIcon(ico)

        errorbox.setText(complete)
        errorbox.exec_()


class Action:
    all = {}

    def __init__(self, name):
        self.name = name

    def __call__(self, function=None):
        if function is not None:
            self.add(self.name, function)
        return function

    @classmethod
    def add(cls, name, function):
        name = '<' + name.lstrip('<').rstrip('>') + '>'

        if name in cls.all.keys():
            raise Exception('{} already registered'.format(name))

        print('adding {}'.format(name))

        cls.all[name] = function


def main(args=None):
    print('starting epyq')

    app = QApplication(sys.argv)
    sys.excepthook = excepthook
    app.setStyleSheet('QMessageBox {{ messagebox-text-interaction-flags: {}; }}'
                      .format(Qt.TextBrowserInteraction))
    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPyQ HMI')

    base_font_size_px = 30


    font_paths = [
        os.path.join(
            QFileInfo.absolutePath(QFileInfo(__file__)),
            '..', 'venv', 'src', 'fontawesome', 'fonts', 'FontAwesome.otf'),
        os.path.join(
            QFileInfo.absolutePath(QFileInfo(__file__)),
            '..', 'venv', 'src', 'metropolis', 'Metropolis-Regular.otf'),
        os.path.join(
            QFileInfo.absolutePath(QFileInfo(__file__)),
            '..', 'venv', 'src', 'metropolis', 'Metropolis-Bold.otf')
    ]

    for font_path in font_paths:
        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QFileInfo(font_path).isAbsolute():
            font_path = os.path.join(
                QFileInfo.absolutePath(QFileInfo(__file__)), font_path)

        QFontDatabase.addApplicationFont(font_path)

    QTextCodec.setCodecForLocale(QTextCodec.codecForName('UTF-8'))

    ui = load_ui('main.ui')

    bus = epyqlib.busproxy.BusProxy()

    list_select = epyqlib.listselect.ListSelect()
    number_pad = epyqlib.numberpad.NumberPad()

    menu_root = epyqlib.listmenu.Node(text='Main Menu')
    menu_model = epyqlib.listmenu.ListMenuModel(root=menu_root)
    menu_view = epyqlib.listmenuview.ListMenuView()

    stacked_manager = StackedManager(stacked=ui.stacked,
                                     list_select=list_select,
                                     menu_model=menu_model,
                                     menu_view=menu_view,
                                     number_pad=number_pad,
                                     bus=bus)

    device_file = 'example_hmi.epc'
    if not QFileInfo(device_file).isFile():
        device_file = os.path.join('..', device_file)

    stacked_manager.add(list_select)

    edit_actions = (
        (stacked_manager.connect_to_list_menu, lambda widget: len(widget.signal_object.enumeration) > 0),
        (stacked_manager.connect_to_numberpad, lambda widget: True)
    )

    device = epyqlib.device.Device(file=device_file,
                                bus=bus,
                                tabs=[],
                                elements=[epyqlib.device.Elements.dash,
                                          epyqlib.device.Elements.nv],
                                rx_interval=0.2,
                                edit_actions=edit_actions)

    # TODO: CAMPid 9757656124812312388543272342377

    default = {
        'Linux': {'bustype': 'socketcan', 'channel': 'can0'},
        'Windows': {'bustype': 'pcan', 'channel': 'PCAN_USBBUS1'}
    }[platform.system()]

    try:
        real_bus = can.interface.Bus(**default,
                                     can_filters=[])
    except Exception:
        if platform.system() == 'Windows':
            real_bus = None
        else:
            raise
    bus.set_bus(bus=real_bus)

    import json
    from collections import OrderedDict

    special_menu_nodes = {}

    Action.add('menu', stacked_manager.to_menu)

    hmi_dialog = epyqlib.hmidialog.HmiDialog()

    nv_filters = []
    if platform.system() != 'Windows':
        nv_filters.append(
            {
                'can_id': device.nvs.status_frames[0].id | socket.CAN_EFF_FLAG,
                'can_mask': socket.CAN_EFF_MASK |
                            socket.CAN_EFF_FLAG |
                            socket.CAN_RTR_FLAG
            }
        )

    names = [
        'SerialNumber',
        'NodeID',
        'Baudrate',
        'ControlSwRev',
        'InterfaceRev',
        'SoftwareHash',
        'BuildTime'
    ]

    inverter_info_nvs = OrderedDict([(name, None) for name in names])

    for frame in device.nvs.set_frames.values():
        for signal in frame.signals:
            if signal.name in inverter_info_nvs.keys():
                inverter_info_nvs[signal.name] = signal

    @Action('inverter_info')
    def inverter_info(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        self.bus.set_filters(nv_filters)

        for nv in inverter_info_nvs.values():
            nv.read_from_device()

        time.sleep(.02)
        app.processEvents()
        rows = []
        for nv in inverter_info_nvs.values():
            name = nv.long_name
            if name is None:
                name = nv.name
            short_string = nv.status_signal.short_string
            rows.append('<td align="right">{} :</td>'
                        '<td align="left" '
                        'style="padding-left:5px;">{}</td>'.format(
                            name, short_string
            ))

        contents = ''.join(['<tr>{}</tr>'.format(row) for row in rows])
        complete = textwrap.dedent('''\
            <table style="width:100%">
                {}
            </table>'''.format(contents))
        hmi_dialog.focus(ok_action=stacked_manager.focus_previous,
                         label=complete,
                         enable_delay=0)

    def modify_node_inverter_info(node):
        node.action = inverter_info

    special_menu_nodes['<inverter_info>'] = modify_node_inverter_info

    playback = Playback(bus=bus)

    def modify_node_playback(node):
        if platform.system() == 'Windows':
            node.action = functools.partial(
                hmi_dialog.focus,
                ok_action=stacked_manager.focus_previous,
                label=textwrap.dedent('''\
                    Playback mode is not supported in Windows.''')
            )
        else:
            node.action = playback.toggle

    Action.add('playback', playback.toggle)

    special_menu_nodes['<playback>'] = modify_node_playback

    def focus_nv(widget):
        bus.set_filters(nv_filters)

        widget.nv.read_from_device()
        ui.stacked.setCurrentWidget(widget)

    def modify_node_nv(node):
        for nv in device.nvs.children:
            widget = epyqlib.parameteredit.ParameterEdit(
                esc_action=stacked_manager.focus_previous,
                edit=number_pad,
                nv=nv,
                dialog=hmi_dialog)

            stacked_manager.add(widget)
            child = epyqlib.listmenu.Node(
                text=nv.name,
                action=functools.partial(
                    focus_nv,
                    widget=widget
                )
            )
            node.append_child(child)

    special_menu_nodes['<nv>'] = modify_node_nv

    def service_restart():
        hmd = epyqlib.wehmd.Wehmd()
        hmd.write_boot_mode(1)
        subprocess.run('reboot')

    @Action('service_reboot')
    def service_reboot_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=service_restart,
                         cancel_action=stacked_manager.focus_previous,
                         label=textwrap.dedent('''\
                             Reboot into maintenance mode?

                             Insert configured USB stick then press OK.'''))

    def modify_node_service_reboot(node):
        node.action = service_reboot_action

    special_menu_nodes['<service_reboot>'] = modify_node_service_reboot

    def calibrate_touchscreen():
        os.remove('/opt/etc/pointercal')
        subprocess.run('reboot')

    @Action('calibrate_touchscreen')
    def calibrate_touchscreen_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=calibrate_touchscreen,
                         cancel_action=stacked_manager.focus_previous,
                         label=textwrap.dedent('''\
                             Reboot and calibrate touchscreen?'''))

    def modify_node_calibrate_touchscreen(node):
        node.action = calibrate_touchscreen_action

    special_menu_nodes['<calibrate_touchscreen>'] = (
        modify_node_calibrate_touchscreen)

    # TODO: CAMPid 93849811216123127753953680713426
    def inverter_to_nv():
        device.nvs.module_to_nv()
        stacked_manager.focus_previous()

    @Action('nv_save')
    def inverter_to_nv_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=inverter_to_nv,
                         cancel_action=stacked_manager.focus_previous,
                         label=textwrap.dedent('''\
                             Save all parameters to NV?'''))

    def modify_node_inverter_to_nv(node):
        node.action = inverter_to_nv_action

    special_menu_nodes['<nv_save>'] = modify_node_inverter_to_nv

    message = [
        'About EPyQ HMI:',
        __copyright__,
        __license__
    ]

    if revision_hash is not None:
        index = round(len(hash) / 2)
        hash = '({first}<br>{second})'.format(first=hash[:index],
                                              second=hash[index:])
    else:
        hash = '{}'.format(revision_hash)

    message.append(hash)

    about_text = '<br>'.join(message)

    @Action('about')
    def about_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=stacked_manager.focus_previous,
                         enable_delay=0,
                         label=about_text)

    def modify_node_about(node):
        node.action = about_action

    special_menu_nodes['<about>'] = modify_node_about

    tooltip_event_filter = TooltipEventFilter(dialog=hmi_dialog,
                                              history=stacked_manager,
                                              parent=app)

    Action.add('tooltip', tooltip_event_filter.action)

    Action.add('menu_root', functools.partial(
        stacked_manager.focus_menu_node,
        node=menu_root
    ))

    def traverse(dict_node, model_node):
        for key, value in dict_node.items():
            if key == '<shortcuts>':
                continue

            child = epyqlib.listmenu.Node(text=key)
            model_node.append_child(child)
            if isinstance(value, OrderedDict):
                traverse(dict_node=value,
                         model_node=child)
            # TODO: CAMPid 139001547845212167972192345189
            elif isinstance(value, QWidget):
                stacked_manager.add(value)
                child.action = functools.partial(
                    stacked_manager.focus_dash,
                    dash=value
                )
            else:
                modify_node = special_menu_nodes.get(value)
                if modify_node is not None:
                    modify_node(child)

                    if value in ['<nv>']:
                        Action.add(value, functools.partial(
                            stacked_manager.focus_menu_node,
                            node=child
                        ))
                else:
                    print("No menu action '{}' found in {}".format(
                             value, special_menu_nodes.keys()),
                          file=sys.stderr)

    traverse(device.ui_paths, menu_root)

    menu_view.setModel(menu_model)
    stacked_manager.add(menu_view)

    ui.shortcut_layout.addStretch(0)

    shortcut_buttons = []

    for icon, action_name in device.ui_paths['<shortcuts>'].items():
        button = ShortcutButton(icon=icon,
                                reference_directory=device.absolute_path())

        ui.shortcut_layout.addWidget(button)

        ui.stacked.currentChanged.connect(button.active_widget_changed)
        menu_model.root_changed.connect(button.active_widget_changed)
        shortcut_buttons.append(button)

        # TODO: CAMPid 139001547845212167972192345189
        if isinstance(action_name, QWidget):
            button.target_widget = action_name
            stacked_manager.add(action_name)
            button.action = functools.partial(
                stacked_manager.focus_dash,
                dash=action_name
            )
        else:
            try:
                action = Action.all[action_name]
            except KeyError:
                print("No action '{}' found in {}".format(
                        action_name,
                        Action.all.keys()
                    ),
                    file=sys.stderr
                )
            else:
                if action_name == '<tooltip>':
                    tooltip_event_filter.trigger_widget = button

                button.action = action

    ui.shortcut_layout.addStretch(0)

    ui.stacked.setCurrentWidget(menu_view)

    stacked_manager.add(hmi_dialog)

    ui.offline_overlay = epyqlib.overlaylabel.OverlayLabel(parent=ui)
    ui.offline_overlay.label.setText('')

    screensaver_image = 'logo_color_inverted.480x272.png'
    if not os.path.isfile(screensaver_image):
        screensaver_image = '/epc/logo.png'

    screensaver_image = QPixmap(screensaver_image)

    timeout = float(device.raw_dict.get('screensaver_timeout', 0))
    if timeout > 0:
        screensaver = Screensaver(application=app,
                                  parent=ui,
                                  pixmap=screensaver_image,
                                  timeout=timeout)

    action_click_handlers = []

    for widget in ui.findChildren(QWidget):
        widget.setProperty('fontawesome',
                           widget.font().family() == 'FontAwesome')
        if widget.property('style_small'):
            widget.setStyleSheet(epyqlib.stylesheets.small.format())

        # TODO: CAMPid 97453289314763416967675427
        if widget.property('editable'):
            dash = widget.parent()
            while dash is not None:
                if dash.property('is_stacked_widget'):
                    break

                dash = dash.parent()

            for action in edit_actions:
                if action[1](widget):
                    action[0](dash=dash,
                              widget=widget,
                              signal=widget.edit)
                    break
        else:
            action_name = widget.property('action')

            if action_name is not None and len(action_name) > 0:

                dash = device.loaded_uis.get(action_name, None)
                if dash is not None:
                    action = functools.partial(
                        stacked_manager.focus_dash,
                        dash=dash
                    )
                else:
                    action = Action.all[action_name]

                handler = ActionClickHandler(action=action)
                action_click_handlers.append(handler)
                widget.installEventFilter(handler)

    app.setStyleSheet(epyqlib.stylesheets.application.format(
        base_font_size_px=base_font_size_px,
        background='black',
        foreground='hsva(0%, 0%, 80%)',
        blue='hsva(80%, 40%, 75%)',
        background_blue='hsva(80%, 40%, 25%)',
        green='hsva(130, 71%, 77%)',
        background_green='hsva(130, 71%, 23%)',
        gray='hsva(0%, 0%, 20%)'
    ))

    if os.environ.get('QT_QPA_PLATFORM', None) == 'linuxfb':
        ui.showFullScreen()
    else:
        ui.show()

    # TODO: CAMPid 98754713241621231778985432
    # ui.menu_button.setMaximumWidth(ui.menu_button.height())

    # TODO: this is a total hack to get these updated...
    menu_view.update_calculated_layout()
    list_select.focus(value=0, action=None, items={})
    list_select.ui.menu_view.update_calculated_layout()
    stacked_manager.to_menu()

    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
