from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag


class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)  # Enable dragging
        self.setAcceptDrops(True)  # Allow dropping
        self.setDragDropMode(QListWidget.InternalMove)  # Enable internal reordering

    def startDrag(self, supportedActions):
        # Define what data to send when dragging starts
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())  # Pass item text as MIME data
            drag.setMimeData(mime_data)
            drag.exec_(supportedActions)

    def dragEnterEvent(self, event):
        # Allow drag-and-drop only if the MIME data format is acceptable
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        # While dragging, allow the event to proceed
        event.accept()

    def dropEvent(self, event):
        # Define what happens when an item is dropped
        if event.mimeData().hasText():
            text = event.mimeData().text()
            self.addItem(text)  # Add the dragged item to the current list
            event.accept()
        else:
            event.ignore()


class DragDropDemo(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Create two drag-and-drop-enabled lists
        self.list1 = DraggableListWidget(self)
        self.list1.addItems(["Item 1", "Item 2", "Item 3"])

        self.list2 = DraggableListWidget(self)
        self.list2.addItems(["Item A", "Item B", "Item C"])

        layout.addWidget(self.list1)
        layout.addWidget(self.list2)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication([])
    window = DragDropDemo()
    window.show()
    app.exec_()
