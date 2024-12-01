# lib/qtwidgets/widsgets/custom_dialogs.py

from PyQt5 import QtWidgets, uic
import os
import sys

from lib.pyqt5 import set_window_geometry_at_cursor

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QListView, QDialogButtonBox, QMessageBox, QPushButton, QTextEdit, QHBoxLayout
from PyQt5.QtCore import QStringListModel, Qt
from PyQt5.QtGui import QIntValidator

class AWSEC2ConfirmationDialog(QDialog):
    def __init__(self, action_desc, formatted_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Action")
        
        # Initialize the layout
        layout = QVBoxLayout(self)

        # Action description label
        total_instances = sum(len(instances) for instances in formatted_data.values())
        total_regions = len(formatted_data)
        action_label = QLabel(f"You are about to perform the following command: {action_desc} "
                              f"on {total_instances} instances in {total_regions} regions.")
        action_label.setWordWrap(True)
        layout.addWidget(action_label)

        # Add region and instance IDs
        for region in sorted(formatted_data.keys()):
            region_label = QLabel(f"Region: {region}")
            region_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(region_label)
            
            instance_ids = ", ".join(instance["InstanceId"] for instance in formatted_data[region])
            instance_text = QTextEdit(instance_ids)
            instance_text.setReadOnly(True)
            instance_text.setFixedHeight(50)  # Adjust height as necessary
            layout.addWidget(instance_text)

        # Add buttons at the bottom
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        proceed_button = QPushButton("Proceed")
        proceed_button.clicked.connect(self.accept)
        button_layout.addWidget(proceed_button)

        layout.addLayout(button_layout)

        # Set dialog layout and properties
        self.setLayout(layout)
        self.setMinimumWidth(400)  # Set a reasonable minimum width
        self.setWindowModality(Qt.ApplicationModal)

    def get_confirmation(self):
        # This method will show the dialog and return True if the user proceeds, False otherwise
        return self.exec_() == QDialog.Accepted
    
class SingleSelectListDialog(QtWidgets.QDialog):
    def __init__(self, items, parent=None):
        super(SingleSelectListDialog, self).__init__(parent)

        # Dynamically construct the path to the UI file
        dir_path = os.path.dirname(os.path.realpath(__file__))
        ui_path = os.path.join(dir_path, '..', 'ui', 'windows', 'singleSelectList_small.ui')

        # Load the UI
        uic.loadUi(ui_path, self)
        
        self.items = items
        self.listView = self.findChild(QtWidgets.QListView, 'listView')
        self.okButton = self.findChild(QtWidgets.QPushButton, 'pushButton')
        self.cancelButton = self.findChild(QtWidgets.QPushButton, 'pushButton_2')
        
        # Setup the model for listView
        model = QStringListModel(self.items)
        self.listView.setModel(model)
        
        # Connect buttons
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        
        # To store the selected item
        self.selectedItem = None

    def accept(self):
        # When OK is clicked, get the selected item
        indexes = self.listView.selectedIndexes()
        if indexes:
            index = indexes[0]
            self.selectedItem = self.items[index.row()]
        super().accept()

def get_user_selection(items):
    app = QtWidgets.QApplication(sys.argv)  # sys.argv handling for QApplication
    dialog = SingleSelectListDialog(items)
    result = dialog.exec_()
    selectedItem = dialog.selectedItem
    return selectedItem, result == QtWidgets.QDialog.Accepted

def get_custom_dialog_data(list1_items, list2_items, title="Custom Dialog", list1_label="List 1", list2_label="List 2", text_input_label="Text Input", int_input_label="Integer Input", text_default="", list1_default=None, list2_default=None, int_default="1"):
    app = QtWidgets.QApplication([])  # sys.argv handling for QApplication
    dialog = CustomDialog(list1_items, list2_items, title, list1_label, list2_label, text_input_label, int_input_label, text_default, list1_default, list2_default, int_default)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        return dialog.getValues()
    return None, None, None, None

class basicForm1TextInput2Lists1IntegerInput(QDialog):
    def __init__(self, list1_items, list2_items, title="Custom Dialog", list1_label="List 1", list2_label="List 2", text_input_label="Text Input", int_input_label="Integer Input", text_default="", list1_default=None, list2_default=None, int_default="1", parent=None):
        super(basicForm1TextInput2Lists1IntegerInput, self).__init__(parent)

        self.setWindowTitle(title)
        set_window_geometry_at_cursor(self, 300, 650)

        layout = QVBoxLayout(self)

        # Text input with label and default
        self.textLabel = QLabel(text_input_label, self)
        layout.addWidget(self.textLabel)
        self.textInput = QLineEdit(self)
        self.textInput.setText(text_default)
        layout.addWidget(self.textInput)

        # First list with label and default selection
        self.list1Label = QLabel(list1_label, self)
        layout.addWidget(self.list1Label)
        self.listView1 = QListView(self)
        model1 = QStringListModel(list1_items)
        self.listView1.setModel(model1)
        if list1_default and list1_default in list1_items:
            index = list1_items.index(list1_default)
            self.listView1.setCurrentIndex(model1.index(index))
        layout.addWidget(self.listView1)

        # Second list with label and default selection
        self.list2Label = QLabel(list2_label, self)
        layout.addWidget(self.list2Label)
        self.listView2 = QListView(self)
        model2 = QStringListModel(list2_items)
        self.listView2.setModel(model2)
        if list2_default and list2_default in list2_items:
            index = list2_items.index(list2_default)
            self.listView2.setCurrentIndex(model2.index(index))
        layout.addWidget(self.listView2)

        # Integer input with label and default
        self.intInputLabel = QLabel(int_input_label, self)
        layout.addWidget(self.intInputLabel)
        self.intInput = QLineEdit(self)
        self.intInput.setValidator(QIntValidator(1, 9999))  # Assuming max value of 9999
        self.intInput.setText(int_default)  # Default value
        layout.addWidget(self.intInput)

        # OK and Exit buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok,
            parent=self,
        )
        self.exitButton = QPushButton("Exit", self)
        self.exitButton.clicked.connect(self.reject)
        self.buttons.addButton(self.exitButton, QDialogButtonBox.RejectRole)

        layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.validateAndAccept)

    def validateAndAccept(self):
        # Check if conditions are met
        if not self.textInput.text() or not self.listView1.currentIndex().isValid() or not self.listView2.currentIndex().isValid():
            QMessageBox.warning(self, "Input Required", "Please provide input for all fields and make selections in both lists.")
            return
        self.accept()

    def getValues(self):
        text_value = self.textInput.text()
        list1_index = self.listView1.currentIndex()
        list1_value = self.listView1.model().data(list1_index, Qt.DisplayRole) if list1_index.isValid() else ""
        list2_index = self.listView2.currentIndex()
        list2_value = self.listView2.model().data(list2_index, Qt.DisplayRole) if list2_index.isValid() else ""
        int_value = self.intInput.text()
        return text_value, list1_value, list2_value, int_value
   