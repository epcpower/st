#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import attr
import can
from epyqlib.abstractcolumns import AbstractColumns
import epyqlib.canneo
import epyqlib.twisted.busproxy
import epyqlib.twisted.nvs
import epyqlib.utils.twisted
import json
import epyqlib.pyqabstractitemmodel
from epyqlib.treenode import TreeNode
from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot)
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
import textwrap
import time
import twisted.internet.defer
import twisted.internet.task

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(AbstractColumns):
    _members = ['name', 'read_only', 'factory', 'value', 'saturate', 'reset',
                'clear', 'default', 'min', 'max', 'comment']

Columns.indexes = Columns.indexes()


class NoNv(Exception):
    pass


class NotFoundError(Exception):
    pass


@attr.s
class Configuration:
    set_frame = attr.ib()
    status_frame = attr.ib()
    to_nv_command = attr.ib()
    to_nv_status = attr.ib()
    read_write_signal = attr.ib()


configurations = {
    'original': Configuration(
        set_frame='CommandSetNVParam',
        status_frame='StatusNVParam',
        to_nv_command='SaveToEE_command',
        to_nv_status='SaveToEE_status',
        read_write_signal='ReadParam_command'
    ),
    'j1939': Configuration(
        set_frame='ParameterQuery',
        status_frame='ParameterResponse',
        to_nv_command='SaveToEE_command',
        to_nv_status='SaveToEE_status',
        read_write_signal='ReadParam_command'
    )
}


@attr.s
class Group(TreeNode):
    fields = attr.ib(default=attr.Factory(Columns))

    def __attrs_post_init__(self):
        super().__init__()


class Nvs(TreeNode, epyqlib.canneo.QtCanListener):
    changed = pyqtSignal(TreeNode, int, TreeNode, int, list)
    set_status_string = pyqtSignal(str)

    def __init__(self, neo, bus, stop_cyclic=None, start_cyclic=None,
                 configuration=None, hierarchy=None, parent=None):
        TreeNode.__init__(self)
        epyqlib.canneo.QtCanListener.__init__(self, parent=parent)

        if configuration is None:
            configuration = 'original'

        self.stop_cyclic = stop_cyclic
        self.start_cyclic = start_cyclic
        self.configuration = configurations[configuration]

        from twisted.internet import reactor
        self.protocol = epyqlib.twisted.nvs.Protocol()
        self.transport = epyqlib.twisted.busproxy.BusProxy(
            protocol=self.protocol,
            reactor=reactor,
            bus=bus)

        self.bus = bus
        self.neo = neo
        self.message_received_signal.connect(self.message_received)


        self.set_frames = [f for f in self.neo.frames
                       if f.name == self.configuration.set_frame]
        try:
            self.set_frames = self.set_frames[0]
        except IndexError:
            # TODO: custom error
            raise NoNv()

        self.set_frames = self.set_frames.multiplex_frames
        self.status_frames = [
            f for f in self.neo.frames
            if f.name == self.configuration.status_frame
        ][0].multiplex_frames

        self.save_frame = None
        self.save_signal = None
        self.save_value = None
        self.confirm_save_frame = None
        self.confirm_save_multiplex_value = None
        self.confirm_save_signal = None
        self.confirm_save_value = None
        for frame in self.set_frames.values():
            for signal in frame.signals:
                if signal.name == self.configuration.to_nv_command:
                    for key, value in signal.enumeration.items():
                        if value == 'Enable':
                            self.save_frame = frame
                            self.save_signal = signal
                            self.save_value = float(key)

        save_status_name = self.configuration.to_nv_status
        for frame in self.status_frames.values():
            for signal in frame.signals:
                if signal.name == save_status_name:
                    for key, value in signal.enumeration.items():
                        if value == 'Enable':
                            self.confirm_save_frame = frame
                            self.confirm_save_multiplex_value = signal.multiplex
                            self.confirm_save_signal = signal
                            self.confirm_save_value = float(key)

        if self.confirm_save_frame is None:
            raise Exception(
                "'{}' signal not found in NV parameter interface".format(
                    save_status_name
                ))

        self.nv_by_path = {}
        # TODO: kind of an ugly manual way to connect this
        self.status_frames[0].set_frame = self.set_frames[0]
        for value, frame in self.set_frames.items():
            signals = [s for s in frame.signals]
            signals = [s for s in signals if s.multiplex is not 'Multiplexor']
            signals = [
                s for s in signals
                if s.name not in [
                    self.configuration.read_write_signal,
                    '{}_MUX'.format(self.configuration.set_frame)
                ]
            ]

            if len(signals) > 0:
                def ignore_timeout(failure):
                    if failure.type is \
                            epyqlib.twisted.nvs.RequestTimeoutError:
                        return None

                    return epyqlib.utils.twisted.errbackhook(
                        failure)

                def send(signals=signals):
                    d = self.protocol.write_multiple(
                        nv_signals=signals,
                        priority=epyqlib.twisted.nvs.Priority.user
                    )
                    d.addErrback(ignore_timeout)

                frame._send.connect(send)

            frame.parameter_signals = []
            for nv in signals:
                if nv.name not in [self.configuration.to_nv_command]:
                    self.nv_by_path[nv.signal_path()] = nv
                    frame.parameter_signals.append(nv)

                nv.frame.status_frame = self.status_frames[value]
                self.status_frames[value].set_frame = nv.frame

                search = (s for s in self.status_frames[value].signals
                          if s.start_bit == nv.start_bit)
                try:
                    nv.status_signal, = search
                except ValueError:
                    raise Exception(
                        'NV status signal not found for {}:{}'.format(nv.frame.mux_name, nv.name)
                    )
                nv.status_signal.set_signal = nv


        unreferenced_paths = set(self.nv_by_path)
        if hierarchy is not None:
            print('yeppers')
            def handle(children, tree_parent,
                       unreferenced_paths=unreferenced_paths):
                unreferenced_groups = []
                print(children, tree_parent)
                for child in children:
                    print(child)
                    if isinstance(child, dict):
                        group = Group(
                            fields=Columns(
                                name=child['name'],
                            )
                        )
                        tree_parent.append_child(group)
                        print('added group: {}'.format(group.fields.name))
                        if child.get('unreferenced'):
                            unreferenced_groups.append(group)
                        else:

                            unreferenced_groups.extend(handle(
                                children=child.get('children', ()),
                                tree_parent=group
                            ))
                    else:
                        path = ('ParameterQuery',) + tuple(child)
                        if path in unreferenced_paths:
                            tree_parent.append_child(self.nv_by_path[path])
                            unreferenced_paths.discard(path)
                        else:
                            raise Exception('Attempted to put parameter in '
                                            'multiple groups: {}'.format(path))

                return tuple(g for g in unreferenced_groups if g is not None)

            unreferenced_groups = handle(children=hierarchy['children'],
                                      tree_parent=self)

            print('\\/ \\/ \\/ unreferenced parameter paths')
            print(
                json.dumps(
                    tuple(p[1:] for p in sorted(unreferenced_paths)),
                    indent=4
                )
            )
            print('/\\ /\\ /\\ unreferenced parameter paths')
        else:
            unreferenced_groups = (self,)

        for group in unreferenced_groups:
            for path in unreferenced_paths:
                group.append_child(self.nv_by_path[path])

        duplicate_names = set()
        found_names = set()
        for child in self.all_nv():
            name = child.fields.name
            if name not in found_names:
                found_names.add(name)
            else:
                duplicate_names.add(name)

        if len(duplicate_names) > 0:
            raise Exception('Duplicate NV parameter names found: {}'.format(
                ', '.join(duplicate_names)))

    def all_nv(self):
        def visit(node, all):
            if isinstance(node, Nv):
                all.add(node)
            else:
                for child in node.children:
                    visit(child, all)

        all = set()
        visit(self, all)

        return all

    def names(self):
        return '\n'.join([n.fields.name for n in self.all_nv()])

    def write_all_to_device(self, only_these=None, callback=None):
        return self._read_write_all(
            read=False,
            only_these=only_these,
            callback=callback,
        )

    def read_all_from_device(self, only_these=None, callback=None):
        return self._read_write_all(
            read=True,
            only_these=only_these,
            callback=callback,
        )

    def _read_write_all(self, read, only_these=None, callback=None):
        activity = ('Reading from device' if read
                    else 'Writing to device')

        self.set_status_string.emit('{}...'.format(activity))
        d = twisted.internet.defer.Deferred()
        d.callback(None)

        already_visited_frames = set()

        def handle_node(node, _=None):
            if not isinstance(node, Nv):
                return

            if node.frame not in already_visited_frames:
                already_visited_frames.add(node.frame)
                node.frame.update_from_signals()
                if read:
                    d.addCallback(
                        lambda _: self.protocol.read(
                            node,
                            priority=epyqlib.twisted.nvs.Priority.user,
                            passive=True,
                            all_values=True,
                        )
                    )
                elif node.frame.read_write.min <= 0:
                    d.addCallback(
                        lambda _: self.protocol.write(
                            node,
                            priority=epyqlib.twisted.nvs.Priority.user,
                            passive=True,
                            all_values=True,
                        )
                    )
                else:
                    return

                if callback is not None:
                    d.addCallback(callback)

        def handle_frame(frame, signals):
                frame.update_from_signals()
                if read:
                    d.addCallback(
                        lambda _: self.protocol.read_multiple(
                            nv_signals=signals,
                            priority=epyqlib.twisted.nvs.Priority.user,
                            passive=True,
                            all_values=True,
                        )
                    )
                elif frame.read_write.min <= 0:
                    d.addCallback(
                        lambda _: self.protocol.write_multiple(
                            nv_signals=signals,
                            priority=epyqlib.twisted.nvs.Priority.user,
                            passive=True,
                            all_values=True,
                        )
                    )
                else:
                    return

                if callback is not None:
                    d.addCallback(callback)

        if only_these is None:
            self.traverse(call_this=handle_node)
        else:
            frames = set(nv.frame for nv in only_these)
            for frame in frames:
                signals = tuple(nv for nv in only_these
                                if nv.frame is frame)

                handle_frame(frame=frame, signals=signals)

        d.addCallback(epyqlib.utils.twisted.detour_result,
                      self.set_status_string.emit,
                      'Finished {}...'.format(activity.lower()))
        d.addErrback(epyqlib.utils.twisted.detour_result,
                     self.set_status_string.emit,
                     'Failed while {}...'.format(activity.lower()))
        d.addErrback(epyqlib.utils.twisted.errbackhook)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        if (msg.arbitration_id == self.status_frames[0].id
                and msg.id_type == self.status_frames[0].extended):
            multiplex_message, multiplex_value =\
                self.neo.get_multiplex(msg)

            if multiplex_message is None:
                return

            if multiplex_value is not None and multiplex_message in self.status_frames.values():
                multiplex_message.unpack(msg.data)
                # multiplex_message.frame.update_canneo_from_matrix_signals()

                status_signals = multiplex_message.signals
                sort_key = lambda s: s.start_bit
                status_signals = sorted(status_signals, key=sort_key)
                set_signals = multiplex_message.set_frame.signals
                set_signals = sorted(set_signals, key=sort_key)
                for status, set in zip(status_signals, set_signals):
                    set.set_value(status.value)

    def unique(self):
        # TODO: actually identify the object
        return '-'

    def to_dict(self, include_secrets=False):
        d = {}
        for child in self.all_nv():
            if include_secrets or not child.secret:
                d[child.fields.name] = child.get_human_value(for_file=True)

        return d

    def from_dict(self, d):
        only_in_file = list(d.keys())

        for child in self.all_nv():
            value = d.get(child.fields.name, None)
            if value is not None:
                child.set_human_value(value)
                only_in_file.remove(child.fields.name)
            else:
                print("Nv value named '{}' not found when loading from dict"
                      .format(child.fields.name))

        for name in only_in_file:
            print("Unrecognized NV value named '{}' found when loading "
                  "from dict".format(name))

    def defaults_from_dict(self, d):
        only_in_file = list(d.keys())

        for child in self.all_nv():
            value = d.get(child.fields.name, None)
            if value is not None:
                child.default_value = child.from_human(float(value))
                only_in_file.remove(child.fields.name)
            else:
                print("Nv value named '{}' not found when loading from dict"
                      .format(child.fields.name))

        for name in only_in_file:
            print("Unrecognized NV value named '{}' found when loading to "
                  "defaults from dict".format(name))

    def module_to_nv(self):
        self.set_status_string.emit('Requested save to NV...')
        self.save_signal.set_value(self.save_value)
        self.save_frame.update_from_signals()
        d = self.protocol.write(self.save_signal, passive=True)
        d.addCallback(self._module_to_nv_response)
        d.addErrback(epyqlib.utils.twisted.errbackhook)

    def _module_to_nv_response(self, result):
        if result == 1:
            feedback = 'Save to NV confirmed'
        else:
            feedback = 'Save to NV failed ({})'.format(
                self.confirm_save_signal.full_string
            )

        self.set_status_string.emit(feedback)

    def logger_set_frames(self):
        frames = [frame for frame in self.set_frames.values()
                  if frame.mux_name.startswith('LoggerChunk')]
        frames.sort(key=lambda frame: frame.mux_name)

        return frames

    def signal_from_names(self, frame_name, value_name):
        frame = [f for f in self.set_frames.values()
                 if f.mux_name == frame_name]

        try:
            frame, = frame
        except ValueError as e:
            raise NotFoundError(
                'Frame not found: {}'.format(frame_name)) from e

        signal = [s for s in frame.signals
                   if s.name == value_name]

        try:
            signal, = signal
        except ValueError as e:
            raise NotFoundError(
                'Signal not found: {}'.format(signal_name)) from e

        return signal


class Nv(epyqlib.canneo.Signal, TreeNode):
    def __init__(self, signal, frame, parent=None):
        epyqlib.canneo.Signal.__init__(self, signal=signal, frame=frame,
                                    parent=parent)
        TreeNode.__init__(self)

        default = self.default_value
        if default is None:
            default = 0

        self.factory = '<factory>' in (self.comment + self.frame.comment)

        self.reset_value = None

        self.clear(mark_modified=False)

        self.fields = Columns(
            name='{}:{}'.format(self.frame.mux_name, self.name),
            value=self.full_string,
            min=self.format_float(value=self.min),
            max=self.format_float(value=self.max),
            default=self.format_strings(value=int(default))[0],
            comment=self.comment,
        )

    def signal_path(self):
        return self.frame.signal_path() + (self.name,)

    def can_be_saturated(self):
        if self.value is None:
            return False

        return self.to_human(self.value) != self.saturation_value()

    def saturate(self):
        if not self.can_be_saturated():
            return

        self.set_data(self.saturation_value(), mark_modified=True)

    def saturation_value(self):
        return min(max(self.min, self.to_human(self.value)), self.max)

    def can_be_reset(self):
        return self.reset_value != self.value

    def reset(self):
        if not self.can_be_reset():
            return

        self.set_value(self.reset_value)

    def set_value(self, value, force=False, check_range=False):
        self.reset_value = value
        epyqlib.canneo.Signal.set_value(self,
                                        value=value,
                                        force=force,
                                        check_range=check_range)
        self.fields.value = self.full_string

    def set_data(self, data, mark_modified=False, check_range=True):
        # self.fields.value = value
        reset_value = self.reset_value
        try:
            if data is None:
                self.set_value(data)
            else:
                self.set_human_value(data, check_range=check_range)
        except ValueError:
            return False
        finally:
            if mark_modified:
                self.reset_value = reset_value
        self.fields.value = self.full_string

        return True

    def can_be_cleared(self):
        return self.value is not None

    def clear(self, mark_modified=True):
        if not self.can_be_cleared():
            return

        self.set_data(None, mark_modified=mark_modified)
        try:
            status_signal = self.status_signal
        except AttributeError:
            pass
        else:
            status_signal.set_value(None)

    def is_factory(self):
        return self.factory

    def is_read_only(self):
        return self.frame.read_write.min > 0

    def unique(self):
        # TODO: make it more unique
        return str(self.fields.name) + '__'


class Frame(epyqlib.canneo.Frame, TreeNode):
    _send = pyqtSignal()

    def __init__(self, message=None, tx=False, frame=None,
                 multiplex_value=None, signal_class=Nv, mux_frame=None,
                 parent=None):
        epyqlib.canneo.Frame.__init__(self, frame=frame,
                                   multiplex_value=multiplex_value,
                                   signal_class=signal_class,
                                   set_value_to_default=False,
                                   mux_frame=mux_frame,
                                   parent=parent)
        TreeNode.__init__(self, parent)

        for signal in self.signals:
            if signal.name in ("ReadParam_command", "ReadParam_status"):
                self.read_write = signal
                break

        for signal in self.signals:
            if signal.name in ("ParameterQuery_MUX", "ParameterResponse_MUX"):
                self.mux = signal
                break

    def signal_path(self):
        if self.mux_name is None:
            return self.name,
        else:
            return self.name, self.mux_name

    def update_from_signals(self, for_read=False, function=None):
        epyqlib.canneo.Frame.update_from_signals(self, function=function)

    def send_now(self):
        self._send.emit()


@attr.s
class Icon:
    character = attr.ib()
    check = attr.ib()
    font = attr.ib(QtGui.QFont('fontawesome'))


class NvModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    set_status_string = pyqtSignal(str)

    def __init__(self, root, parent=None):
        editable_columns = Columns.fill(False)
        editable_columns.value = True

        epyqlib.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, editable_columns=editable_columns,
                alignment=Qt.AlignVCenter | Qt.AlignLeft, parent=parent)

        self.headers = Columns(name='Name',
                               value='Value',
                               min='Min',
                               max='Max',
                               default='Default',
                               comment='Comment')

        root.set_status_string.connect(self.set_status_string)

        self.icons = Columns(
            reset=Icon(character='\uf0e2', check='can_be_reset'),
            clear=Icon(character='\uf057', check='can_be_cleared'),
            saturate=Icon(character='\uf066', check='can_be_saturated'),
            factory=Icon(character='\uf084', check='is_factory'),
            read_only=Icon(character='\uf023', check='is_read_only')
        )

        self.icon_columns = set(
            index
            for index, icon in zip(self.icons.indexes, self.icons)
            if icon is not None
        )

        self.force_action_decorations = False

    def all_nv(self):
        return self.root.all_nv()

    def flags(self, index):
        flags = super().flags(index)
        node = self.node_from_index(index)

        if not isinstance(node, epyqlib.nv.Nv) or node.is_read_only():
            flags &= ~Qt.ItemIsEditable

        return flags

    def data_font(self, index):
        icon = self.icons[index.column()]
        if icon is not None:
            return icon.font

        return None

    def data_display(self, index):
        column = index.column()
        icon = self.icons[column]
        if icon is not None:
            if self.force_action_decorations:
                return icon.character
            else:
                node = self.node_from_index(index)
                if isinstance(node, epyqlib.nv.Nv):
                    check = getattr(node, icon.check)
                    if check():
                        return icon.character

        return super().data_display(index)

    def data_tool_tip(self, index):
        if index.column() == Columns.indexes.saturate:
            node = self.node_from_index(index)
            if isinstance(node, epyqlib.nv.Nv):
                if node.can_be_saturated():
                    return node.format_strings(
                        value=node.from_human(node.saturation_value()))[0]
        if index.column() == Columns.indexes.reset:
            node = self.node_from_index(index)
            if isinstance(node, epyqlib.nv.Nv):
                if node.can_be_reset():
                    return node.format_strings(value=node.reset_value)[0]
        elif index.column() == Columns.indexes.comment:
            node = self.node_from_index(index)
            if isinstance(node, epyqlib.nv.Nv):
                comment = node.fields.comment
                if comment is None:
                    comment = ''
                return '\n'.join(textwrap.wrap(comment, 60))

    def saturate_node(self, node):
        node.saturate()
        self.changed(node, 0, node, len(Columns()), [])

    def reset_node(self, node):
        node.reset()
        self.changed(node, 0, node, len(Columns()), [])

    def clear_node(self, node):
        node.clear()
        self.changed(node, 0, node, len(Columns()), [])

    def setData(self, index, data, role=None):
        if index.column() == Columns.indexes.value:
            if role == Qt.EditRole:
                node = self.node_from_index(index)
                success = node.set_data(data, mark_modified=True)

                self.dataChanged.emit(index, index)
                return success

        return False

    @pyqtSlot()
    def module_to_nv(self):
        # TODO: monitor and report success/failure of write
        self.root.module_to_nv()

    @pyqtSlot()
    def write_to_module(self):
        # TODO: device or module!?!?
        self.root.write_all_to_device()

    @pyqtSlot()
    def read_from_module(self):
        self.root.read_all_from_device()

    @pyqtSlot()
    def write_to_file(self, parent=None):
        filters = [
            ('EPC Parameters', ['epp']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(
            filters, save=True, parent=parent)

        if filename is None:
            return

        if len(filename) > 0:
            with open(filename, 'w') as file:
                d = self.root.to_dict()
                s = json.dumps(d, sort_keys=True, indent=4)
                file.write(s)
                file.write('\n')

                self.set_status_string.emit(
                    'Saved to "{}"'.format(filename)
                )

    @pyqtSlot()
    def read_from_file(self, parent=None):
        filters = [
            ('EPC Parameters', ['epp']),
            ('All Files', ['*'])
        ]
        filename = epyqlib.utils.qt.file_dialog(filters, parent=parent)

        if filename is None:
            return

        if len(filename) > 0:
            with open(filename, 'r') as file:
                s = file.read()
                d = json.loads(s)
                self.root.from_dict(d)

                self.set_status_string.emit(
                    'Loaded from "{}"'.format(filename)
                )


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
