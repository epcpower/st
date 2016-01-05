import can
import epyq.canneo
from PyQt5.QtCore import (Qt, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSignal, pyqtSlot,
                          QTimer)
from PyQt5 import QtWidgets

# See file COPYING in this source tree
__copyright__ = 'Copyright 2015, EPC Power Corp.'
__license__ = 'GPLv2+'


class TreeNode:
    def __init__(self,  tx=False, parent=None):
        self.last = None

        self.tx = tx

        self.tree_parent = None
        self.set_parent(parent)
        self.children = []

    def set_parent(self, parent):
        self.tree_parent = parent
        if self.tree_parent is not None:
            self.tree_parent.append_child(self)

    def append_child(self, child):
        self.children.append(child)
        child.tree_parent = self

    def child_at_row(self, row):
        return self.children[row]

    def row_of_child(self, child):
        for i, item in enumerate(self.children):
            if item == child:
                return i
        return -1

    def remove_child(self, row):
        value = self.children[row]
        self.children.remove(value)

        return True

    def __len__(self):
        return len(self.children)


class MessageNode(epyq.canneo.Frame, TreeNode):
    def __init__(self, message=None, tx=False, frame=None, parent=None):
        epyq.canneo.Frame.__init__(self, frame=frame, parent=parent)
        TreeNode.__init__(self, parent)

        self.fields = Columns.none()
        self.last_time = None

        self.tx = tx
        self._send_checked = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._send)

        try:
            for signal in self.frame._signals:
                self.append_child(SignalNode(signal, frame=self, tx=self.tx))
        except KeyError:
            pass

        # TODO: quit doing this frame->fields in two places (098098234709572943)
        format = '0x{{:0{}X}}'
        if frame._extended:
            format = format.format(8)
        else:
            format = format.format(3)

        self.fields = Columns(id=format.format(self.frame._Id),
                              message=self.frame._name,
                              signal='',
                              length='{} B'.format(self.frame._Size),
                              value='-',
                              dt=None)

        if message is not None:
            self.extract_message(message)

    @property
    def send_checked(self):
        return self._send_checked

    @send_checked.setter
    def send_checked(self, value):
        old = self._send_checked

        # TODO: move this validation to dt to check itself
        if isinstance(self.dt, float):
            self._send_checked = value
        elif value == Qt.Unchecked:
            self._send_checked = value
        else:
            # TODO: notify user why it's not accepted
            raise ValueError('Unable to check send checkbox due to invalid dt')

        if self._send_checked != old:
            self.update_timer()

    @property
    def dt(self):
        return self.fields.dt

    @dt.setter
    def dt(self, value):
        old = self.fields.dt

        if value == '':
            self.fields.dt = value
            self.send_checked = Qt.Unchecked
        else:
            # TODO: move this validation to dt to check itself
            check_it = not isinstance(self.fields.dt, float)
            self.fields.dt = float(value)
            if check_it:
                self.send_checked = Qt.Checked

        if self.fields.dt != old:
            self.update_timer()

    def update_timer(self):
        if self.send_checked == Qt.Unchecked:
            self.timer.stop()
        else:
            self.timer.setInterval(int(self.dt * 1000))
            if not self.timer.isActive():
                self.timer.start()

    def extract_message(self, message, verify=True):
        # TODO: stop calling this from txrx and use the standard Frame reception

        if verify:
            # TODO: make sure the message matches the id/type and length
            pass

        # TODO: I think this is not needed
        # self.message = message

        # TODO: quit doing this frame->fields in two places (098098234709572943)
        # TODO: should this formatting be done in the other place?
        format = '0x{{:0{}X}}'
        if message.id_type:
            format = format.format(8)
        else:
            format = format.format(3)

        self.fields.id = format.format(message.arbitration_id)

        try:
            self.fields.message = self.frame._name
        except AttributeError:
            self.fields.message = '-'

        self.fields.length = '{} B'.format(message.dlc)
        self.fields.signal = ''
        # TODO: quit repeating (98476589238759)
        self.fields.value = ' '.join(['{:02X}'.format(byte) for byte in message.data])
        if self.last_time == message.timestamp:
            raise Exception('message already received {message}'
                            .format(**locals()))
        if self.last_time is None:
            self.fields.dt = '-'
        else:
            self.fields.dt = '{:.4f}'.format(message.timestamp - self.last_time)
        self.last_time = message.timestamp

        epyq.canneo.Frame.message_received(self, message)

    def unique(self):
        return self.fields.id

    def set_data(self, data):
        self.fields.value = data
        self.update()
        self.frame.update_from_signals()

class SignalNode(epyq.canneo.Signal, TreeNode):
    def __init__(self, signal, frame, tx=False, connect=None, tree_parent=None, parent=None):
        epyq.canneo.Signal.__init__(self, signal=signal, frame=frame, connect=connect, parent=parent)
        TreeNode.__init__(self, tx=tx, parent=tree_parent)

        self.fields = Columns(id=self.signal.getMsbReverseStartbit(),
                              message='',
                              signal=signal._name,
                              length='{} b'.format(signal._signalsize),
                              value='-',
                              dt=None)
        self.last_time = None

    def unique(self):
        # TODO: make it more unique
        return str(self.fields.id) + '__'

    def set_value(self, value):
        epyq.canneo.Signal.set_value(self, value)
        self.fields.value = self.full_string

    def set_data(self, data):
        self.set_human_value(data)
        self.frame.update_from_signals()


class TxRx(TreeNode, epyq.canneo.QtCanListener):
    # TODO: just Rx?
    changed = pyqtSignal(TreeNode, int, TreeNode, int)
    added = pyqtSignal(TreeNode)

    def __init__(self, tx, matrix=None, bus=None, parent=None):
        TreeNode.__init__(self)
        epyq.canneo.QtCanListener.__init__(self, parent=parent)

        self.bus = bus

        self.tx = tx
        self.rx = not self.tx
        self.matrix = matrix
        self.messages = {}

        if self.rx:
            self.message_received_signal.connect(self.message_received)

        if self.tx:
            for frame in self.matrix._fl._list:
                try:
                    frames = frame.multiplex_frames
                except AttributeError:
                    frames = [(None, frame)]
                else:
                    frames = frames.items()

                for value, frame in frames:
                    message = can.Message()
                    message.arbitration_id = frame._Id
                    message.id_type = frame._extended
                    message.dlc = frame._Size
                    for signal in frame._signals:
                        if signal._multiplex == 'Multiplexor':
                            signal.signal.set_value(value)
                    message.data = frame.frame.pack(frame.frame)
                    self.add_message(message=message, tx=True)


    def set_node_id(self, node_id):
        # TODO: I think this can go away
        self.node_id = node_id

    def add_message(self, message=can.Message(), id=None, tx=False):
        frame = self.get_multiplex(message)[0]

        if id is None:
            id = self.generate_id(message=message)

        message_node = frame.frame
        message_node.send.connect(self.send)
        self.messages[id] = message_node
        self.append_child(message_node)
        self.added.emit(message_node)

    def get_multiplex(self, message):
        base_frame = self.matrix.frameById(message.arbitration_id)
        try:
            frame = base_frame.multiplex_frame
        except AttributeError:
            frame = base_frame
            multiplex_value = None
        else:
            # finish the multiplex thing
            frame.frame.unpack(message.data)
            multiplex_value = base_frame.multiplex_signal.signal.value
            # TODO: stop using strings for integers...
            frame = base_frame.multiplex_frames[str(multiplex_value)]

        return (frame, multiplex_value)

    def generate_id(self, message):
        multiplex_value = self.get_multiplex(message)[1]

        return (message.arbitration_id,
                message.id_type,
                multiplex_value)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        id = self.generate_id(message=msg)

        try:
            self.messages[id].extract_message(msg)
            # TODO: be more judicious in describing what changed
            #       and also don't change just column 5...
            self.changed.emit(self.messages[id], Columns.indexes.value,
                              self.messages[id], Columns.indexes.dt)
            self.changed.emit(self.messages[id].children[0], Columns.indexes.value,
                              self.messages[id].children[-1], Columns.indexes.value)
        except KeyError:
            self.add_message(message=msg,
                             id=id)

    def unique(self):
        # TODO: actually identify the object
        return '-'

    @pyqtSlot(can.Message)
    def send(self, message):
        self.bus.send(message)

    def __str__(self):
        return 'Indexes: \n' + '\n'.join([str(i) for i in self.children])


class Columns:
    def __init__(self, id, length, message, signal, value, dt):
        self.id = id
        self.length = length
        self.message = message
        self.signal = signal
        self.value = value
        self.dt = dt

    def none():
        return Columns(None, None, None, None, None, None)

    def __len__(self):
        return 6

    def __getitem__(self, index):
        if index == Columns.indexes.id:
            return self.id
        if index == Columns.indexes.length:
            return self.length
        if index == Columns.indexes.message:
            return self.message
        if index == Columns.indexes.signal:
            return self.signal
        if index == Columns.indexes.value:
            return self.value
        if index == Columns.indexes.dt:
            return self.dt

        raise IndexError('column index out of range')

Columns.indexes = Columns(0, 1, 2, 3, 4, 5)


class TxRxModel(QAbstractItemModel):
    # TODO: seems like a lot of boilerplate which could be put in an abstract class
    #       (wrapping the abstract class?  hmmm)

    def __init__(self, root, parent=None):
        QAbstractItemModel.__init__(self, parent=parent)

        self.root = root
        self.headers = Columns(id='ID',
                               length='Length',
                               message='Message',
                               signal='Signal',
                               value='Value',
                               dt='dt')

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[section])
        return QVariant()

    def flags(self, index):
        flags = QAbstractItemModel.flags(self, index)

        node = self.node_from_index(index)
        if node.tx:
            if index.column() == Columns.indexes.value:
                try:
                    multiplex = node.signal._multiplex
                except AttributeError:
                    allow = True
                else:
                    allow = multiplex != 'Multiplexor'

                if allow:
                    flags |= Qt.ItemIsEditable

            if index.column() == Columns.indexes.dt:
                if isinstance(node, MessageNode):
                    flags |= Qt.ItemIsEditable
                    flags |= Qt.ItemIsUserCheckable

        return flags

    def setData(self, index, data, role=None):
        if index.column() == Columns.indexes.value:
            if role == Qt.EditRole:
                node = self.node_from_index(index)
                node.set_data(data)
                self.dataChanged.emit(index, index)
                return True

        if index.column() == Columns.indexes.dt:
            if role == Qt.EditRole:
                node = self.node_from_index(index)
                try:
                    node.dt = data
                except ValueError:
                    return False

                self.dataChanged.emit(index, index)
                return True
            if role == Qt.CheckStateRole:
                node = self.node_from_index(index)
                node.send_checked = data
                return True

        return False

    def index(self, row, column, parent):
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))
        # if not parent.isValid():
        #     parent_item = self.root
        # else:
        #     parent_item = parent.internalPointer()
        #
        # child_item = parent_item.children[row]
        # if child_item:
        #     return self.createIndex(row, column, child_item)
        # else:
        #     return QModelIndex()

    def data(self, index, role):
        if role == Qt.DecorationRole:
            return QVariant()

        if role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignTop | Qt.AlignLeft))

        if role == Qt.CheckStateRole:
            if index.column() == Columns.indexes.dt:
                if self.root.tx:
                    node = self.node_from_index(index)
                    try:
                        return node.send_checked
                    except AttributeError:
                        return QVariant()

        if role == Qt.DisplayRole:
            node = self.node_from_index(index)

            if index.column() == len(self.headers):
                return QVariant(node.unique())
            else:
                try:
                    return QVariant(node.fields[index.column()])
                except IndexError:
                    return QVariant()

        if role == Qt.EditRole:
            node = self.node_from_index(index)
            value = node.fields[index.column()]

            # TODO: totally dt specific
            if isinstance(value, float):
                string = str(value)
            else:
                string = ''

            return QVariant(string)

        return QVariant()

    def columnCount(self, parent):
        return len(self.headers)

    def rowCount(self, parent):
        node = self.node_from_index(parent)
        if node is None:
            return 0
        return len(node)

    def parent(self, child):
        if not child.isValid():
            return QModelIndex()

        node = self.node_from_index(child)

        if node is None:
            return QModelIndex()

        parent = node.tree_parent

        if parent is None:
            return QModelIndex()

        grandparent = parent.tree_parent
        if grandparent is None:
            return QModelIndex()
        row = grandparent.row_of_child(parent)

        assert row != - 1
        return self.createIndex(row, 0, parent)

    def node_from_index(self, index):
        if index.isValid():
            return index.internalPointer()
        else:
            return self.root

    def index_from_node(self, node):
        # TODO  make up another role for identification?
        try:
            return node.index
        except AttributeError:
            node.index = self.match(self.index(0, len(self.headers), QModelIndex()),
                                    Qt.DisplayRole,
                                    node.unique(),
                                    1,
                                    Qt.MatchRecursive)[0]

        return node.index

    @pyqtSlot(TreeNode, int, TreeNode, int)
    def changed(self, start_node, start_column, end_node, end_column):
        start_index = self.index_from_node(start_node)
        start_index = self.index(start_index.row(), start_column, start_index.parent())
        if end_node is not start_node:
            end_index = self.index_from_node(end_node)
            end_index = self.index(end_index.row(), end_column, end_index.parent())
        else:
            end_index = start_index
        self.dataChanged.emit(start_index, end_index)

    @pyqtSlot(TreeNode)
    def added(self, message):
        # TODO: this is just a tad bit broad...
        self.beginResetModel()
        self.endResetModel()


class ValueDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, model, parent):
        QtWidgets.QStyledItemDelegate.__init__(self, parent=parent)

        self.model = model

    def createEditor(self, parent, option, index):
        # TODO: way too particular
        node = self.model.node_from_index(index)

        try:
            items = node.enumeration_strings()
        except AttributeError:
            pass
        else:
            if len(items) > 0:
                combo = QtWidgets.QComboBox(parent=parent)

                # TODO: use the userdata to make it easier to get in and out
                combo.addItems(items)

                present_string = node.fields[index.column()]
                index = combo.findText(present_string)
                if index == -1:
                    combo.setCurrentIndex(0);
                else:
                    combo.setCurrentIndex(index);

                combo.currentIndexChanged.connect(self.current_index_changed)

                return combo

        return QtWidgets.QStyledItemDelegate.createEditor(
            self, parent, option, index)

    @pyqtSlot()
    def current_index_changed(self):
        self.commitData.emit(self.sender())
