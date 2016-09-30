#!/usr/bin/env python3

# TODO: get some docstrings in here!

# TODO: CAMPid 98852142341263132467998754961432
import epyq.tee
import os
import sys

log = open(os.path.join(os.getcwd(), 'epyq.log'), 'w', encoding='utf-8', buffering=1)

if sys.stdout is None:
    sys.stdout = log
else:
    sys.stdout = epyq.tee.Tee([sys.stdout, log])

if sys.stderr is None:
    sys.stderr = log
else:
    sys.stderr = epyq.tee.Tee([sys.stderr, log])

try:
    import epyq.revision
except ImportError:
    pass
else:
    print(epyq.revision.hash)

import can
import canmatrix.importany as importany
import copy
import epyq.widgets.abstractwidget
import epyq.busproxy
import epyq.canneo
import epyq.device
import epyq.hmidialog
import epyq.listmenuview
import epyq.listselect
import epyq.numberpad
import epyq.nv
import epyq.parameteredit

try:
    import epyq.revision
except ImportError:
    pass

from epyq.svgwidget import SvgWidget
import epyq.txrx
import epyq.wehmd
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


class StackedHistory:
    def __init__(self, stacked_widget, length=20):
        self.stacked_widget = stacked_widget
        self.length = length

        self.stacked_widget.currentChanged.connect(self.changed)

        self.history = []

    def changed(self, index):
        self.history.append(index)
        self.history = self.history[-self.length:]

    def focus_previous(self, steps=1):
        self.stacked_widget.setCurrentIndex(self.history[-(steps+1)])


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

    stacked_history = StackedHistory(ui.stacked)

    bus = epyq.busproxy.BusProxy()

    device_file = 'example_hmi.epc'
    if not QFileInfo(device_file).isFile():
        device_file = os.path.join('..', device_file)

    def add_stacked_widget(widget):
        ui.stacked.addWidget(widget)
        widget.setProperty('is_stacked_widget', True)

    number_pad = epyq.numberpad.NumberPad()
    add_stacked_widget(number_pad)


    def set_widget_value(dash, widget, value):
        if value is not None:
            widget.user_set_value(value)
        ui.stacked.setCurrentWidget(dash)

    def trigger_numberpad(dash, widget):
        number_pad.focus(value=widget.signal_object.get_human_value(),
                         action=functools.partial(
                             set_widget_value, widget=widget, dash=dash),
                         label='{} [{}]'.format(widget.ui.label.text(),
                                                widget.ui.units.text()))

    def connect_to_numberpad(dash, widget, signal):
        signal.connect(functools.partial(
            trigger_numberpad,
            dash=dash,
            widget=widget
        ))


    list_select = epyq.listselect.ListSelect()
    add_stacked_widget(list_select)

    def set_widget_value_from_list(dash, widget, value):
        if value is not None:
            widget.user_set_value(value)
        ui.stacked.setCurrentWidget(dash)

    def trigger_list_menu(dash, widget):
        signal = widget.signal_object
        items = {key: value
                 for key, value in signal.enumeration.items()
                 if signal.min <= key <= signal.max}

        list_select.focus(value=widget.signal_object.get_human_value(),
                          action=functools.partial(
                              set_widget_value_from_list,
                              widget=widget,
                              dash=dash),
                          items=items,
                          label='{}'.format(widget.ui.label.text()))

    def connect_to_list_menu(dash, widget, signal):
        signal.connect(functools.partial(
            trigger_list_menu,
            dash=dash,
            widget=widget
        ))

    edit_actions = (
        (connect_to_list_menu, lambda widget: len(widget.signal_object.enumeration) > 0),
        (connect_to_numberpad, lambda widget: True)
    )

    device = epyq.device.Device(file=device_file,
                                bus=bus,
                                tabs=[],
                                elements=[epyq.device.Elements.dash,
                                          epyq.device.Elements.nv],
                                rx_interval=0.5,
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
    actions = {}

    def to_menu(auto_level_up=True, check=False):
        if check:
            return menu_view == ui.stacked.currentWidget()

        if bus.bus is not None:
            try:
                bus.bus.setFilters(can_filters=[])
            except AttributeError:
                # Just an optimization so can be skipped
                pass
        if menu_view == ui.stacked.currentWidget() and auto_level_up:
            menu_view.ui.esc_button.clicked.emit()
        else:
            ui.stacked.setCurrentWidget(menu_view)

    actions['<menu>'] = to_menu

    hmi_dialog = epyq.hmidialog.HmiDialog()

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

    def inverter_info(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        if bus.bus is not None:
            try:
                bus.bus.setFilters(nv_filters)
            except AttributeError:
                # Just an optimization so can be skipped
                pass

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
        hmi_dialog.focus(ok_action=stacked_history.focus_previous,
                         label=complete,
                         enable_delay=0)

    def modify_node_inverter_info(node):
        node.action = inverter_info

    actions['<inverter_info>'] = inverter_info
    special_menu_nodes['<inverter_info>'] = modify_node_inverter_info

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

    playback = Playback(bus=bus)

    def modify_node_playback(node):
        if platform.system() == 'Windows':
            node.action = functools.partial(
                hmi_dialog.focus,
                ok_action=stacked_history.focus_previous,
                label=textwrap.dedent('''\
                    Playback mode is not supported in Windows.''')
            )
        else:
            node.action = playback.toggle

    actions['<playback>'] = playback
    special_menu_nodes['<playback>'] = modify_node_playback

    def focus_nv(widget):
        if bus.bus is not None:
            try:
                bus.bus.setFilters(nv_filters)
            except AttributeError:
                # Just an optimization so can be skipped
                pass

        widget.nv.read_from_device()
        ui.stacked.setCurrentWidget(widget)

    def modify_node_nv(node):
        for nv in device.nvs.children:
            widget = epyq.parameteredit.ParameterEdit(
                edit=number_pad,
                nv=nv,
                dialog=hmi_dialog)

            add_stacked_widget(widget)
            child = epyq.listmenu.Node(
                text=nv.name,
                action=functools.partial(
                    focus_nv,
                    widget=widget
                )
            )
            node.append_child(child)

    special_menu_nodes['<nv>'] = modify_node_nv

    def service_restart():
        hmd = epyq.wehmd.Wehmd()
        hmd.write_boot_mode(1)
        subprocess.run('reboot')

    def service_reboot_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=service_restart,
                         cancel_action=stacked_history.focus_previous,
                         label=textwrap.dedent('''\
                             Reboot into maintenance mode?

                             Insert configured USB stick then press OK.'''))

    def modify_node_service_reboot(node):
        node.action = service_reboot_action

    actions['<service_reboot>'] = service_reboot_action
    special_menu_nodes['<service_reboot>'] = modify_node_service_reboot

    def calibrate_touchscreen():
        os.remove('/opt/etc/pointercal')
        subprocess.run('reboot')

    def calibrate_touchscreen_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=calibrate_touchscreen,
                         cancel_action=stacked_history.focus_previous,
                         label=textwrap.dedent('''\
                             Reboot and calibrate touchscreen?'''))

    def modify_node_calibrate_touchscreen(node):
        node.action = calibrate_touchscreen_action

    actions['<calibrate_touchscreen>'] = calibrate_touchscreen_action
    special_menu_nodes['<calibrate_touchscreen>'] = (
        modify_node_calibrate_touchscreen)

    # TODO: CAMPid 93849811216123127753953680713426
    def inverter_to_nv():
        device.nvs.module_to_nv()
        stacked_history.focus_previous()

    def inverter_to_nv_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=inverter_to_nv,
                         cancel_action=stacked_history.focus_previous,
                         label=textwrap.dedent('''\
                             Save all parameters to NV?'''))

    def modify_node_inverter_to_nv(node):
        node.action = inverter_to_nv_action

    actions['<nv_save>'] = inverter_to_nv_action
    special_menu_nodes['<nv_save>'] = modify_node_inverter_to_nv

    message = [
        'About EPyQ HMI:',
        __copyright__,
        __license__
    ]

    try:
        hash = epyq.revision.hash
    except AttributeError:
        pass
    else:
        index = round(len(hash) / 2)
        hash = '({first}<br>{second})'.format(first=hash[:index],
                                              second=hash[index:])
        message.append(hash)

    about_text = '<br>'.join(message)

    def about_action(check=False):
        if check:
            try:
                raise Exception('`check` not supported')
            except:
                traceback.print_exc()
            return False

        hmi_dialog.focus(ok_action=stacked_history.focus_previous,
                         enable_delay=0,
                         label=about_text)

    def modify_node_about(node):
        node.action = about_action

    actions['<about>'] = about_action
    special_menu_nodes['<about>'] = modify_node_about

    menu_root = epyq.listmenu.Node(text='Main Menu')

    def focus_dash(dash, check=False):
        if check:
            return ui.stacked.currentWidget() == dash

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
        if bus.bus is not None:
            try:
                bus.bus.setFilters(filters)
            except AttributeError:
                # Just an optimization so can be skipped
                pass
        ui.stacked.setCurrentWidget(dash)

    def repolish(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    class ShortcutButton(QPushButton):
        def __init__(self, *args, **kwargs):
            QPushButton.__init__(self, *args, **kwargs)
            self.target_widget = None
            self._active = False
            self.active = False
            self.action = None

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
        def __init__(self, parent=None, trigger_widget=None):
            QObject.__init__(self, parent)
            self.trigger_widget = trigger_widget

        def deactivate(self):
            app.removeEventFilter(self)
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
                tooltip_event_filter.deactivate()
            else:
                self.trigger_widget.setProperty('active', True)
                repolish(self.trigger_widget)
                app.installEventFilter(tooltip_event_filter)

        def eventFilter(self, object, event):
            if (isinstance(event, QMouseEvent)
                    and event.button() == Qt.LeftButton
                    and event.type() == QEvent.MouseButtonRelease):
                self.deactivate()

                widget = app.widgetAt(event.globalPos())
                while not isinstance(
                        widget, epyq.widgets.abstractwidget.AbstractWidget):
                    if widget is None:
                        break
                    widget = widget.parent()
                else:
                    hmi_dialog.focus(
                        ok_action=stacked_history.focus_previous,
                        label=widget.toolTip(),
                        enable_delay=0
                    )

                return True

            return False

    tooltip_event_filter = TooltipEventFilter()

    actions['<tooltip>'] = tooltip_event_filter.action

    menu_model = epyq.listmenu.ListMenuModel(root=menu_root)
    menu_view = epyq.listmenuview.ListMenuView()

    def focus_menu_node(node=None, check=False):
        if check:
            return (ui.stacked.currentWidget() == menu_view
                    and node == menu_model.root)

        to_menu(auto_level_up=False)
        if node not in [None, menu_model.root]:
            menu_model.node_clicked(node)

    def traverse(dict_node, model_node):
        for key, value in dict_node.items():
            if key == '<shortcuts>':
                continue

            child = epyq.listmenu.Node(text=key)
            model_node.append_child(child)
            if isinstance(value, OrderedDict):
                traverse(dict_node=value,
                         model_node=child)
            # TODO: CAMPid 139001547845212167972192345189
            elif isinstance(value, QWidget):
                add_stacked_widget(value)
                child.action = functools.partial(
                    focus_dash,
                    dash=value
                )
            else:
                try:
                    modify_node = special_menu_nodes[value]
                except KeyError:
                    print("No menu action '{}' found in {}".format(
                            value,
                            special_menu_nodes.keys()),
                        file=sys.stderr
                    )
                else:
                    modify_node(child)

                    if value in ['<nv>']:
                        actions[value] = functools.partial(
                            focus_menu_node,
                            node=child
                        )

    traverse(device.ui_paths, menu_root)

    menu_view.setModel(menu_model)
    add_stacked_widget(menu_view)

    ui.shortcut_layout.addStretch(0)

    shortcut_buttons = []

    for icon, action_name in device.ui_paths['<shortcuts>'].items():
        button = ShortcutButton()

        if os.path.splitext(icon)[1] in ['.svg', '.png']:
            button.setIcon(QIcon(device.absolute_path(icon)))
        else:
            base = 16 if icon.startswith('0x') else 10
            character = chr(int(icon, base))
            button.setText(character)

        button.setFont(QFont('FontAwesome'))

        ui.shortcut_layout.addWidget(button)

        button.target_widget = None
        ui.stacked.currentChanged.connect(button.active_widget_changed)
        menu_model.root_changed.connect(button.active_widget_changed)
        button.clicked.connect(button.trigger_action)
        shortcut_buttons.append(button)

        # TODO: CAMPid 139001547845212167972192345189
        if isinstance(action_name, QWidget):
            button.target_widget = action_name
            add_stacked_widget(action_name)
            button.action = functools.partial(
                focus_dash,
                dash=action_name
            )
        else:
            try:
                action = actions[action_name]
            except KeyError:
                print("No action '{}' found in {}".format(
                        action_name,
                        actions.keys()
                    ),
                    file=sys.stderr
                )
            else:
                if action_name == '<tooltip>':
                    tooltip_event_filter.trigger_widget = button

                button.action = action

    ui.shortcut_layout.addStretch(0)

    ui.stacked.setCurrentWidget(menu_view)

    add_stacked_widget(hmi_dialog)

    if platform.system() == 'Linux':
        styles = {
            'red': "background-color: rgba(255, 255, 255, 0);"
                                   "color: rgba(255, 85, 85, 255);"
                                    "font-size: 20px;",
            'blue': "background-color: rgba(255, 255, 255, 0);"
                                   "color: rgba(85, 85, 255, 255);"
        }

        ui.offline_overlay = epyq.overlaylabel.OverlayLabel(parent=ui)
        ui.offline_overlay.label.setText('bbbbbbbbbbb')
        ui.offline_overlay.label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        ui.offline_overlay.setStyleSheet(styles['red'])
        ui.offline_overlay.label.setStyleSheet('font-size: 10px;')

        # top_process = subprocess.Popen(
        #     ['top', '-b'],
        #     shell=True,
        #     stdin=subprocess.PIPE,
        #     stdout=subprocess.PIPE,
        #     bufsize=1
        # )

        # grep_process = subprocess.Popen(
        #     # ['grep', '-Ei', "'^%?cpu'"],
        #     ['grep', '-i', 'cpu'],
        #     shell=True,
        #     stdin=top_process.stdout,
        #     stdout=subprocess.PIPE,
        #     bufsize=1
        # )


        #
        # cpu_usage_process = subprocess.Popen(
        #     # ["top -b | grep -Ei '^%?cpu'"],
        #     ["echo red'"],
        #     shell=True,
        #     stdin=subprocess.PIPE,
        #     stdout=subprocess.PIPE,
        #     bufsize=1
        # )

        # import select
        # p = select.poll()
        # p.register(top_process.stdout)

        # while True:
        #     if len(p.poll(1)) > 0:
        #         print(top_process.stdout.readline())
        #     time.sleep(0.1)

        from linux_metrics import cpu_stat

        print(linux_metrics.cpu_stat.cpu_percent())


        def update_cpu_usage():
            with open('/proc/loadavg') as file:
                load = file.read()

            # print(cpu_usage_process.communicate()[0])
            # with open('/proc/stat', 'r') as procfile:
            #     cputimes = procfile.readline()
            #     cputotal = 0
            #     # count from /proc/stat: user, nice, system, idle, iowait, irc, softirq, steal, guest
            #     for i in cputimes.split(' ')[2:]:
            #         i = int(i)
            #         cputotal = (cputotal + i)
            #     cpu = float(cputotal)
            #
            # ui.offline_overlay.label.setText('\n'.join([load, str(cpu)]))

        timer = QTimer()
        timer.timeout.connect(update_cpu_usage)
        timer.setInterval(1000)
        timer.start()
        update_cpu_usage()

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

    action_click_handlers = []

    for widget in ui.findChildren(QWidget):
        widget.setProperty('fontawesome',
                           widget.font().family() == 'FontAwesome')
        if widget.property('style_small'):
            widget.setStyleSheet('''
                QWidget[fontawesome=false] {{
                    font-size: 15px;
                }}

                QPushButton[fontawesome=false] {{
                    min-height: 25px;
                }}

                QLineEdit, QPushButton {{
                    border-radius: 5px;
                }}
            '''.format())

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
                try:
                    dash = device.loaded_uis[action_name]
                except KeyError:
                    action = actions[action_name]
                else:
                    action = functools.partial(
                        focus_dash,
                        dash=dash
                    )

                handler = ActionClickHandler(action=action)
                action_click_handlers.append(handler)
                widget.installEventFilter(handler)

    app.setStyleSheet('''
        QWidget {{
            font-size: {base_font_size_px}px;
            qproperty-focusPolicy: NoFocus;
            color: {foreground};
        }}

        QWidget#MainForm {{
            background-color: {background};
        }}

        QWidget[fontawesome=false] {{
            font-family: Metropolis;
        }}

        QWidget[fontawesome=true] {{
            font-size: 36px;
            icon-size: 36px
        }}

        Epc {{
            qproperty-show_enumeration_value: false;
        }}

        QAbstractScrollArea {{
            qproperty-frameShape: NoFrame;
        }}

        QPushButton {{
            font-size: {base_font_size_px}px;
            min-width: 40px;
            min-height: 40px;
            max-height: 40px;
            color: black;
        }}

        QPushButton[fontawesome=true] {{
            min-width: 46px;
            max-width: 46px;
            min-height: 46px;
            max-height: 46px;
        }}

        QFrame {{
            qproperty-frameShadow: Plain;
        }}

        QLineEdit, QPushButton {{
            border-radius: 10px;
            border-width: 0px;
            border-style: solid;
        }}

        QLineEdit {{
            qproperty-focusPolicy: NoFocus;
            background-color: {background_blue};
        }}

        QPushButton:enabled {{
            background-color: {green};
        }}

        QPushButton:!enabled {{
            background-color: {gray};
        }}

        QPushButton[active=true] {{
            background: {blue};
        }}

        QLineEdit {{
            qproperty-frame: false;
        }}

        QLineEdit:!enabled {{
            background-color: {gray};
        }}

        QLineEdit:enabled {{
            padding: 0 8px;
            selection-background-color: darkgray;
        }}

        QSlider {{
            min-height: 40px;
            min-width: 30px;
        }}

        QSlider::groove {{
            width: 4px;
            border-radius: 2px;
            background-color: {gray};
        }}

        QSlider::handle {{
            height: 10px;
            border-radius: 3px;
            margin: 0 -8px;
            background-color: {blue};
        }}
    '''.format(
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
    to_menu()

    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
