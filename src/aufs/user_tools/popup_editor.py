import os
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, QGridLayout, QComboBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from editable_pandas_model import EditablePandasModel

class PopupEditor(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(f"Editing: {file_path}")
        self.resize(1000, 800)
        self.file_path = file_path
        self.dataframe = None

        # === Load the CSV into a DataFrame ===
        self.load_csv()

        # === Main Layout ===
        self.main_layout = QVBoxLayout(self)

        # === Initialize EditablePandasModel ===
        self.model = EditablePandasModel(self.dataframe, editable=True)

        # === Central Layout ===
        self.central_layout = QHBoxLayout()

        # === Left side vertical button layout ===
        self.left_button_layout = QVBoxLayout()

        # Add Row button (full height)
        self.add_row_button = QPushButton("Add Row", self)
        self.left_button_layout.addWidget(self.add_row_button)

        # Move Row Up/Down buttons (stacked vertically, full height)
        self.move_row_up_button = QPushButton("Move Row Up", self)
        self.move_row_down_button = QPushButton("Move Row Down", self)
        self.left_button_layout.addWidget(self.move_row_up_button)
        self.left_button_layout.addWidget(self.move_row_down_button)

        # Add the left button layout to the central layout
        self.central_layout.addLayout(self.left_button_layout)

        # === TableView for displaying the DataFrame ===
        self.table_view = QTableView(self)
        self.table_view.setModel(self.model)
        self.central_layout.addWidget(self.table_view)

        # === Top button layout (above the table) ===
        self.top_button_layout = QGridLayout()

        # Add Column button (first row)
        self.add_column_button = QPushButton("Add Column", self)
        self.top_button_layout.addWidget(self.add_column_button, 0, 0)

        # Move Column Left/Right buttons (second row)
        self.move_column_left_button = QPushButton("Move Column Left", self)
        self.move_column_right_button = QPushButton("Move Column Right", self)
        self.top_button_layout.addWidget(self.move_column_left_button, 1, 0)
        self.top_button_layout.addWidget(self.move_column_right_button, 1, 1)

        # Sort Column button (third row)
        self.sort_column_button = QPushButton("Sort Column", self)
        self.top_button_layout.addWidget(self.sort_column_button, 2, 0)

        # Clear Selected Data button (fourth row)
        self.clear_selection_button = QPushButton("Clear Selected Data", self)
        self.top_button_layout.addWidget(self.clear_selection_button, 3, 0)

        # === Data Type Dropdown ===
        self.dtype_dropdown = QComboBox(self)
        self.dtype_dropdown.addItems(self.model.get_valid_dtypes())
        self.top_button_layout.addWidget(self.dtype_dropdown, 4, 0)

        # Set Column Type button (fifth row)
        self.set_column_type_button = QPushButton("Set Column Type", self)
        self.top_button_layout.addWidget(self.set_column_type_button, 4, 1)

        # Add top buttons above the table
        self.main_layout.addLayout(self.top_button_layout)
        
        # Add the central layout (table and buttons) to the main layout
        self.main_layout.addLayout(self.central_layout)

        # === Footer buttons (below the table) ===
        self.footer_layout = QHBoxLayout()

        # Reload button
        self.reload_button = QPushButton("Reload", self)
        self.footer_layout.addWidget(self.reload_button)

        # Save and Exit buttons
        self.save_button = QPushButton("Save", self)
        self.exit_button = QPushButton("Exit", self)
        self.footer_layout.addWidget(self.save_button)
        self.footer_layout.addWidget(self.exit_button)

        # Add footer buttons to the main layout
        self.main_layout.addLayout(self.footer_layout)

        # === Button Connections ===
        self.add_row_button.clicked.connect(self.add_row)
        self.add_column_button.clicked.connect(self.add_column)
        self.move_row_up_button.clicked.connect(self.move_row_up)
        self.move_row_down_button.clicked.connect(self.move_row_down)
        self.move_column_left_button.clicked.connect(self.move_column_left)
        self.move_column_right_button.clicked.connect(self.move_column_right)
        self.sort_column_button.clicked.connect(self.sort_column)
        self.clear_selection_button.clicked.connect(self.clear_selected_data)
        self.set_column_type_button.clicked.connect(self.set_column_type)
        self.reload_button.clicked.connect(self.reload_csv)
        self.save_button.clicked.connect(self.save_csv)
        self.exit_button.clicked.connect(self.close)

    def load_csv(self):
        """Load the CSV file into a Pandas DataFrame."""
        try:
            if os.path.exists(self.file_path):
                self.dataframe = pd.read_csv(self.file_path)
                
                # Handle the case where the CSV is empty
                if self.dataframe.empty:
                    QMessageBox.warning(self, "Empty File", f"{self.file_path} is empty.")
                    self.dataframe = pd.DataFrame()  # Create an empty DataFrame if CSV is empty
            else:
                QMessageBox.warning(self, "File Not Found", f"{self.file_path} does not exist.")
                self.dataframe = pd.DataFrame()  # Create an empty DataFrame if file is not found
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load {self.file_path}: {str(e)}")
            self.dataframe = pd.DataFrame()  # Create an empty DataFrame on failure

    def save_csv(self):
        """Save the edited DataFrame back to the CSV file."""
        print(f"Saving file to: {self.file_path}")
        try:
            self.model.get_dataframe().to_csv(self.file_path, index=False)
            QMessageBox.information(self, "Success", "Changes saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save {self.file_path}: {str(e)}")

    def reload_csv(self):
        """Reload the CSV file and discard any unsaved changes."""
        reply = QMessageBox.question(self, 'Confirm Reload', 
                                     "Are you sure you want to reload the file? All unsaved changes will be lost.", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.load_csv()
            self.model.update_dataframe(self.dataframe)

    def add_row(self):
        """Adds a new row at the bottom."""
        self.model.add_row()

    # Adding a new column
    def add_column(self):
        column_name, ok = QInputDialog.getText(self, "Add Column", "Column name:")
        if ok and column_name:
            self.model.add_column(column_name=column_name)

    def move_row_up(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.move_row(index.row(), -1)

    def move_row_down(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.move_row(index.row(), 1)

    def move_column_left(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.move_column(index.column(), -1)

    def move_column_right(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.move_column(index.column(), 1)

    def sort_column(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.sort_column(index.column())

    def clear_selected_data(self):
        """Clear the data in the currently selected cells."""
        selection_model = self.table_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        self.model.clear_selection(selected_indexes)

    def set_column_type(self):
        """Sets the column's data type based on the dropdown selection."""
        index = self.table_view.currentIndex()
        if index.isValid():
            selected_dtype = self.dtype_dropdown.currentText()
            self.model.set_column_dtype(index.column(), selected_dtype)
