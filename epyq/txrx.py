import can
import canmatrix.canmatrix
from epyq.abstractcolumns import AbstractColumns
import epyq.canneo
from epyq.treenode import TreeNode
from PyQt5.QtCore import (Qt, QVariant, QModelIndex, pyqtSignal, pyqtSlot,
                          QTimer)

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class MessageNode(epyq.canneo.Frame, TreeNode):
    def __init__(self, message=None, tx=False, frame=None, parent=None):
        epyq.canneo.Frame.__init__(self, frame=frame, parent=parent)
        TreeNode.__init__(self, parent)

        self.fields = Columns()
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

        identifier = epyq.canneo.format_identifier(frame._Id, frame._extended)

        self.fields = Columns(id=identifier,
                              name=self.frame._name,
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
        if not isinstance(self.dt, float):
            if value != Qt.Unchecked:
                self.dt = 0.1

        self._send_checked = value

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

        self.fields.id = epyq.canneo.format_identifier(
                message.arbitration_id, message.id_type)

        try:
            self.fields.name = self.frame._name
        except AttributeError:
            self.fields.name = '-'

        self.fields.length = '{} B'.format(message.dlc)
        self.fields.value = epyq.canneo.format_data(message.data)
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

    def update_from_signals(self):
        epyq.canneo.Frame.update_from_signals(self)
        self.fields.value = epyq.canneo.format_data(self.data)
        # TODO: send should update, not the other way around like it is
        self._send()


class SignalNode(epyq.canneo.Signal, TreeNode):
    def __init__(self, signal, frame, tx=False, connect=None, tree_parent=None, parent=None):
        epyq.canneo.Signal.__init__(self, signal=signal, frame=frame, connect=connect, parent=parent)
        TreeNode.__init__(self, tx=tx, parent=tree_parent)

        self.fields = Columns(id=self.signal.getMsbReverseStartbit(),
                              name=signal._name,
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
        try:
            self.set_human_value(data)
        except ValueError:
            raise
        else:
            self.frame.update_from_signals()


class TxRx(TreeNode, epyq.canneo.QtCanListener):
    # TODO: just Rx?
    changed = pyqtSignal(TreeNode, int, TreeNode, int, list)
    begin_insert_rows = pyqtSignal(TreeNode, int, int)
    end_insert_rows = pyqtSignal()

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
                    message.data = frame.frame.pack(frame.frame)
                    self.add_message(message=message, tx=True)

        # TODO: this should probably be done in the view but this is easier for now
        #       Tx can't be added to later (yet)
        #       Rx will add in order received
        self.children.sort(key=lambda c: c.frame._name)

    def set_node_id(self, node_id):
        # TODO: I think this can go away
        self.node_id = node_id

    def add_message(self, message=can.Message(), id=None, tx=False):
        frame = epyq.canneo.get_multiplex(self.matrix, message)[0]

        if id is None:
            id = self.generate_id(message=message)

        if frame is not None:
            message_node = frame.frame
        else:
            frame = canmatrix.canmatrix.Frame(
                bid=message.arbitration_id,
                name='',
                size=message.dlc,
                transmitter=None
            )
            message_node = MessageNode(message=message, tx=tx, frame=frame)
            self.matrix._fl.addFrame(frame)

        message_node.send.connect(self.send)
        self.messages[id] = message_node

        index = len(self.children)
        # TODO: move to TreeNode?
        self.begin_insert_rows.emit(self, index, index)
        self.append_child(message_node)
        self.end_insert_rows.emit()

    def generate_id(self, message):
        multiplex_value = epyq.canneo.get_multiplex(self.matrix, message)[1]

        return (message.arbitration_id,
                message.id_type,
                multiplex_value)

    @pyqtSlot(can.Message)
    def message_received(self, msg):
        id = self.generate_id(message=msg)

        try:
            message = self.messages[id]
        except KeyError:
            self.add_message(message=msg,
                             id=id)
            message = self.messages[id]

        self.messages[id].extract_message(msg)
        # TODO: for some reason this doesn't seem to needed and
        #       significantly (3x) increases cpu usage
        # self.changed.emit(self.messages[id], Columns.indexes.value,
        #                   self.messages[id], Columns.indexes.dt)
        if len(self.messages[id].children) > 0:
            self.changed.emit(
                self.messages[id].children[0], Columns.indexes.value,
                self.messages[id].children[-1], Columns.indexes.value,
                [Qt.DisplayRole])

    def unique(self):
        # TODO: actually identify the object
        return '-'

    @pyqtSlot(can.Message)
    def send(self, message):
        self.bus.send(message)

    def __str__(self):
        return 'Indexes: \n' + '\n'.join([str(i) for i in self.children])


class Columns(AbstractColumns):
    _members = ['id', 'length', 'name', 'value', 'dt']

Columns.indexes = Columns.indexes()


class TxRxModel(epyq.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, parent=None):
        checkbox_columns = Columns.fill(False)
        if root.tx:
            checkbox_columns.dt = True

        epyq.pyqabstractitemmodel.PyQAbstractItemModel.__init__(
                self, root=root, checkbox_columns=checkbox_columns,
                parent=parent)

        self.headers = Columns(id='ID',
                               length='Length',
                               name='Name',
                               value='Value',
                               dt='dt')

    def flags(self, index):
        flags = epyq.pyqabstractitemmodel.PyQAbstractItemModel.flags(self, index)

        node = self.node_from_index(index)
        if node.tx:
            if index.column() == Columns.indexes.value:
                try:
                    multiplex = node.signal._multiplex
                except AttributeError:
                    allow = isinstance(node, SignalNode)
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
                try:
                    node.set_data(data)
                except ValueError:
                    return False
                else:
                    self.dataChanged.emit(index, index)
                    return True

            return False

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
