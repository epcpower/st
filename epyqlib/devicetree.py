#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import can
import epyqlib.pyqabstractitemmodel
import functools
import logging
import sys
import time

from collections import OrderedDict
from epyqlib.abstractcolumns import AbstractColumns
from epyqlib.treenode import TreeNode
from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot,
                          QPersistentModelIndex)
from PyQt5.QtWidgets import QFileDialog

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(AbstractColumns):
    _members = ['name', 'bitrate', 'transmit']

Columns.indexes = Columns.indexes()

bitrates = OrderedDict([
    (1000000, '1 MBit/s'),
    (500000, '500 kBit/s'),
    (250000, '250 kBit/s'),
    (125000, '125 kBit/s')
])

default_bitrate = 500000

def available_buses():
    valid = []

    for interface in can.interface.VALID_INTERFACES:
        if interface == 'pcan':
            for n in range(1, 9):
                channel = 'PCAN_USBBUS{}'.format(n)
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append({'interface': interface,
                                  'channel': channel})
        elif interface == 'kvaser':
            # TODO: get the actual number of available devices rather
            #       than hard coding?
            #
            #       can.interfaces.kvaser.canGetNumberOfChannels())
            for channel in range(0, 8):
                try:
                    bus = can.interface.Bus(bustype=interface,
                                            channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append({'interface': interface,
                                  'channel': channel})
        elif interface == 'socketcan':
            for n in range(9):
                channel = 'can{}'.format(n)
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append({'interface': interface,
                                  'channel': channel})
            for n in range(9):
                channel = 'vcan{}'.format(n)
                try:
                    bus = can.interface.Bus(bustype=interface, channel=channel)
                except:
                    pass
                else:
                    bus.shutdown()
                    valid.append({'interface': interface,
                                  'channel': channel})
        else:
            print('Availability check not implemented for {}'
                  .format(interface), file=sys.stderr)

    return valid


class Bus(TreeNode):
    def __init__(self, interface, channel):
        TreeNode.__init__(self)

        self.interface = interface
        self.channel = channel

        self.bitrate = default_bitrate
        self.separator = ' - '

        if self.interface is not None:
            name = '{}{}{}'.format(self.interface,
                                   self.separator,
                                   self.channel)
        else:
            name = 'Offline'

        self.fields = Columns(name=name,
                              bitrate=bitrates[self.bitrate],
                              transmit='')

        self._checked = Columns.fill(Qt.Unchecked)

        self.bus = epyqlib.busproxy.BusProxy(
            transmit=self.checked(Columns.indexes.transmit))

    def terminate(self):
        self.bus.terminate()
        logging.debug('{} terminated'.format(object.__repr__(self)))

    def set_data(self, data):
        for key, value in bitrates.items():
            if data == value:
                self.bitrate = key
                self.fields.bitrate = data

                self.set_bus()

        raise ValueError('{} not found in {}'.format(
            data,
            ', '.join(bitrates.values())
        ))

    def enumeration_strings(self, include_values=False):
        return bitrates.values()

    def unique(self):
        return '{} - {}'.format(self.interface, self.channel)

    def append_child(self, child):
        TreeNode.append_child(self, child)

    def checked(self, column):
        return self._checked[column]

    def set_checked(self, checked, column):
        if column in [Columns.indexes.name, Columns.indexes.transmit]:
            if self.interface is None:
                self._checked[column] = Qt.Unchecked

                return

            self._checked[column] = checked

            if self._checked[column] == Qt.Checked:
                for device in self.children:
                    if device.checked(column) != Qt.Unchecked:
                        device.set_checked(checked=Qt.Checked,
                                           column=column)
            elif self._checked[column] == Qt.Unchecked:
                for device in self.children:
                    if device.checked(column) != Qt.Unchecked:
                        device.set_checked(checked=Qt.PartiallyChecked,
                                           column=column)

            if column == Columns.indexes.name:
                self.set_bus()
            elif column == Columns.indexes.transmit:
                self.bus.transmit = checked == Qt.Checked

    def set_bus(self):
        if self.interface == None:
            return

        self.bus.set_bus(None)

        if self._checked.name == Qt.Checked:
            real_bus = can.interface.Bus(bustype=self.interface,
                                         channel=self.channel,
                                         bitrate=self.bitrate)
            # TODO: Yuck, but it helps recover after connecting to a bus with
            #       the wrong speed.  So, find a better way.
            time.sleep(0.5)
        else:
            real_bus = None

        self.bus.set_bus(bus=real_bus)


class Device(TreeNode):
    def __init__(self, device):
        TreeNode.__init__(self)

        self.fields = Columns(name=device.name,
                              bitrate='',
                              transmit='')

        self._checked = Columns.fill(Qt.Unchecked)

        self.device = device
        self.device.bus.transmit = self._checked.transmit == Qt.Checked

    def terminate(self):
        self.device.terminate()
        logging.debug('{} terminated'.format(object.__repr__(self)))

    def unique(self):
        return self.device

    def checked(self, column):
        return self._checked[column]

    def set_checked(self, checked, column):
        if column in [Columns.indexes.name, Columns.indexes.transmit]:
            if checked == Qt.Checked:
                if self.tree_parent.checked(column) == Qt.Checked:
                    self._checked[column] = Qt.Checked
                else:
                    if self._checked[column] == Qt.Unchecked:
                        self._checked[column] = Qt.PartiallyChecked
                    else:
                        self._checked[column] = Qt.Unchecked
            elif checked == Qt.PartiallyChecked:
                self._checked[column] = Qt.PartiallyChecked
            else:
                self._checked[column] = Qt.Unchecked

            self.device.bus_status_changed(
                online=self._checked.name == Qt.Checked,
                transmit=self._checked.transmit == Qt.Checked)

            if column == Columns.indexes.name:
                if self._checked[column] == Qt.Unchecked:
                    self.device.bus.set_bus()
                else:
                    self.device.bus.set_bus(self.tree_parent.bus)

            elif column == Columns.indexes.transmit:
                self.device.bus.transmit = self._checked[column] == Qt.Checked


class Tree(TreeNode):
    def __init__(self):
        TreeNode.__init__(self)


class Model(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    device_removed = pyqtSignal(epyqlib.device.Device)

    def __init__(self, root, parent=None):
        buses = [{'interface': None, 'channel': None}] + available_buses()
        for bus in buses:
            bus = Bus(interface=bus['interface'],
                      channel=bus['channel'])
            root.append_child(bus)
            went_offline = functools.partial(self.went_offline, node=bus)
            bus.bus.went_offline.connect(went_offline)

        editable_columns = Columns.fill(False)
        editable_columns.bitrate = True

        checkbox_columns = Columns.fill(False)
        checkbox_columns.name = True
        checkbox_columns.transmit = True

        epyqlib.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, editable_columns=editable_columns,
                checkbox_columns=checkbox_columns, parent=parent)

        self.headers = Columns(name='Name',
                               bitrate='Bitrate',
                               transmit='Transmit')

    def terminate(self):
        def terminate_devices(node, _):
            if isinstance(node, Device):
                node.terminate()

        def terminate_buses(node, _):
            if isinstance(node, Bus):
                node.terminate()

        self.root.traverse(terminate_devices, internal_nodes=True)
        self.root.traverse(terminate_buses, internal_nodes=True)
        logging.debug('{} terminated'.format(object.__repr__(self)))

    def went_offline(self, node):
        # TODO: trigger gui update, or find a way that does it automatically
        node.set_checked(checked=Qt.Unchecked,
                         column=Columns.indexes.name)
        self.changed(node, Columns.indexes.name,
                     node, Columns.indexes.name,
                     [Qt.CheckStateRole])

    def setData(self, index, data, role=None):
        if index.column() == Columns.indexes.bitrate:
            if role == Qt.EditRole:
                node = self.node_from_index(index)
                try:
                    node.set_data(data)
                except ValueError:
                    return False
                self.dataChanged.emit(index, index)
                return True
        elif index.column() in [Columns.indexes.name, Columns.indexes.transmit]:
            if role == Qt.CheckStateRole:
                node = self.node_from_index(index)

                node.set_checked(checked=data, column=index.column())

                # TODO: CAMPid 9349911217316754793971391349
                children = len(node.children)
                if children > 0:
                    self.changed(node.children[0], Columns.indexes[0],
                                 node.children[-1], Columns.indexes[-1],
                                 [Qt.CheckStateRole])

                return True

        return False

    def add_device(self, bus, device):
        index = len(bus.children)

        # TODO: move to TreeNode?
        self.begin_insert_rows(bus, index, index)
        bus.append_child(device)
        self.end_insert_rows()

        persistent_index = QPersistentModelIndex(self.index_from_node(bus))
        self.layoutChanged.emit([persistent_index])

    def remove_device(self, device):
        bus = device.tree_parent
        row = bus.children.index(device)

        device.device.bus.set_bus()

        self.begin_remove_rows(bus, row, row)
        bus.remove_child(row)
        self.end_remove_rows()

        persistent_index = QPersistentModelIndex(self.index_from_node(bus))
        self.layoutChanged.emit([persistent_index])

        self.device_removed.emit(device.device)

    def device_from_widget(self, widget):
        def check(node, matches, widget=widget):
            if isinstance(node, Device) and node.device.ui is widget:
                matches.append(node.device)

        matches = []
        self.root.traverse(call_this=check, payload=matches)

        if len(matches) == 0:
            return None

        device, = matches

        return device

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
