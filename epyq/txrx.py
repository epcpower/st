import can
import epyq.canneo
from PyQt5.QtCore import (Qt, QAbstractItemModel, QVariant,
                          QModelIndex, pyqtSignal, pyqtSlot)


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
    def __init__(self, message, tx=False, frame=None, parent=None):
        epyq.canneo.Frame.__init__(self, frame=frame, parent=parent)
        TreeNode.__init__(self, parent)

        self.fields = Columns.none()
        self.last_time = None

        self.tx = tx

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
            raise Exception('message already received')
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
        s = self.signal
        v = str(self.value)
        try:
            value = '{} ({})'.format(s._values[str(v)], v)
        except KeyError:
            value = v

        if s._unit is not None:
            if len(s._unit) > 0:
                value += ' [{}]'.format(s._unit)
        self.fields.value = value

    def set_data(self, data):
        self.value = data
        self.fields.value = data
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
                message = can.Message()
                message.arbitration_id = frame._Id
                message.id_type = frame._extended
                message.dlc = frame._Size
                self.add_message(message, tx=True)

    def set_node_id(self, node_id):
        # TODO: I think this can go away
        self.node_id = node_id

    def add_message(self, message=can.Message(), tx=False):
        try:
            frame = self.matrix.frameById(message.arbitration_id)
        except AttributeError:
            frame = None

        id = (message.arbitration_id, message.id_type)

        message_node = frame.frame
        message_node.send.connect(self.send)
        self.messages[id] = message_node
        self.append_child(message_node)
        self.added.emit(message_node)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        id = (msg.arbitration_id, msg.id_type)

        try:
            self.messages[id].extract_message(msg)
            # TODO: be more judicious in describing what changed
            #       and also don't change just column 5...
            self.changed.emit(self.messages[id], Columns.indexes.value,
                              self.messages[id], Columns.indexes.dt)
            self.changed.emit(self.messages[id].children[0], Columns.indexes.value,
                              self.messages[id].children[-1], Columns.indexes.value)
        except KeyError:
            self.add_message(msg)

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

        # TODO: only if Tx
        if self.node_from_index(index).tx:
            if index.column() == Columns.indexes.value:
                flags |= Qt.ItemIsEditable

        return flags

    def setData(self, index, data, role=None):
        if role == Qt.EditRole:
            node = self.node_from_index(index)
            node.set_data(data)
            self.dataChanged.emit(index, index)
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

        if role != Qt.DisplayRole:
            return QVariant()

        node = self.node_from_index(index)

        if index.column() == len(self.headers):
            return QVariant(node.unique())
        else:
            try:
                return QVariant(node.fields[index.column()])
            except IndexError:
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


