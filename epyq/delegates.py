from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtWidgets


class Combo(QtWidgets.QStyledItemDelegate):
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


class Button(QtWidgets.QStyledItemDelegate):
    def __init__(self, model, parent):
        QtWidgets.QStyledItemDelegate.__init__(self, parent=parent)

        self.model = model

    def createEditor(self, parent, option, index):
        # TODO: way too particular
        node = self.model.node_from_index(index)

        try:
            text = node.button_text(index.column())
        except AttributeError:
            pass
        else:
            button = QtWidgets.QPushButton(parent=parent)
            button.setText(text)
            return button

        return QtWidgets.QStyledItemDelegate.createEditor(
            self, parent, option, index)

    @pyqtSlot()
    def current_index_changed(self):
        self.commitData.emit(self.sender())
