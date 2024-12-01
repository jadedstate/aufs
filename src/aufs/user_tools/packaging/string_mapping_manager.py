# src/aufs/user_tools/packaging/string_mapping_manager.py

import os
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QMessageBox, QComboBox, QLabel, QFrame, QTextEdit, QFileDialog, QApplication, 
                               QListWidget, QListWidgetItem, QDialog, QCheckBox)
from PySide6.QtCore import QObject, Signal
import pandas as pd

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.deep_editor import DeepEditor  # The CSV editor component
from src.aufs.user_tools.packaging.string_remapper import StringRemapper  # The remapping logic class

class StringMappingManager(QWidget):
    selected_rows_updated = Signal(pd.DataFrame)

    def __init__(self, csv_path=None, root_path=None, recipient=None, user=None, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path
        self.root_path = root_path  # Added root_path
        self.recipient = recipient  # Added recipient
        self.user = user  # Added user
        self.setWindowTitle(f"CSV and Remap Tool: {os.path.basename(self.csv_path) if self.csv_path else 'Untitled'}")
        self.resize(1000, 900)

        self.selected_rows_df = pd.DataFrame()  # Store selected rows
        self.remapper = StringRemapper(root_path=root_path, recipient=recipient, user=user)

        self.button_flags = {'save': False, 'exit': False, 'add_row': False, 'delete_row': False, 'move_row_up': False, 'move_row_down': False}
        
        # Main layout
        self.main_layout = QVBoxLayout(self)

        # === CSV Editor ===
        self.deep_editor = DeepEditor(file_path=self.csv_path, button_flags=self.button_flags, file_type='csv', parent=self)
        self.main_layout.addWidget(self.deep_editor)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)

        # === Remapping Section ===
        remap_layout = QVBoxLayout()
        
        # Header selection dropdown
        remap_layout.addWidget(QLabel("Choose ID Header:"))
        self.id_header_dropdown = QComboBox()
        self.id_header_dropdown.currentIndexChanged.connect(self.populate_id_value_list)
        remap_layout.addWidget(self.id_header_dropdown)

        # ID value list
        remap_layout.addWidget(QLabel("Select ID Value(s):"))
        self.id_value_list = QListWidget()
        self.id_value_list.setSelectionMode(QListWidget.MultiSelection)
        remap_layout.addWidget(self.id_value_list)

        # Select All / None Toggle
        toggle_layout = QHBoxLayout()
        self.select_all_toggle = QCheckBox("Select All/None")
        self.select_all_toggle.stateChanged.connect(self.toggle_all_id_values)
        toggle_layout.addWidget(self.select_all_toggle)

        # "Set Selection" Button
        self.set_selection_button = QPushButton("Set Selection")
        self.set_selection_button.clicked.connect(self.set_selection)
        toggle_layout.addWidget(self.set_selection_button)
        # remap_layout.addLayout(toggle_layout)

        # "Delete DF Data" Button
        self.delete_df_button = QPushButton("Delete DF Data")
        self.delete_df_button.clicked.connect(self.clear_selected_data)
        toggle_layout.addWidget(self.delete_df_button)

        remap_layout.addLayout(toggle_layout)

        # Results display pane (also used to show selected_rows_df)
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        remap_layout.addWidget(self.results_display)

        # Add remapping layout to main layout
        self.main_layout.addLayout(remap_layout)

        # Load headers if a CSV is provided
        if self.csv_path:
            self.load_csv()

    def map_requested_values(self, id_header, id_value, target_columns, virtual_headers, ignore_columns, use_dialog, root_job_path=None, row_data=None, remap_type='string', use_custom_remapper=True):
        """
        Perform remapping with optional row_data and remap_type arguments.

        Parameters:
        - id_header (str): The column header to match.
        - id_value (str): The ID value to find in the specified header column.
        - target_columns (list): List of columns to remap.
        - row_data (pd.Series): Optional row data to pass directly to the remapper.
        - remap_type (str): Optional remap type to specify how remapping is handled.

        Returns:
        - list: Result of the remapping operation.
        """
        if not target_columns:
            QMessageBox.warning(self, "Input Error", "Please fill in all fields.")
            return

        # Fetch the latest mappings DataFrame from DeepEditor and set it in StringRemapper
        mappings_df = self.deep_editor.model.get_dataframe()
        if mappings_df is not None:
            self.remapper.set_mappings(mappings_df)
        else:
            QMessageBox.critical(self, "Error", "Failed to retrieve mappings DataFrame.")
            return

        # Perform remapping and display results
        try:
            result = self.remapper.remap(id_header,
                                         id_value,
                                         target_columns,
                                         virtual_headers,
                                         row_data=row_data,
                                         remap_type=remap_type,
                                         use_custom_remapper=use_custom_remapper,
                                         ignore_columns=ignore_columns,
                                         use_dialog=use_dialog,
                                         root_job_path=root_job_path                                         
                                         )
            # self.display_results(result)
            return result
        except Exception as e:
            QMessageBox.critical(self, "Remap Error", f"Failed to remap values: {str(e)}")

    def initialize_manager_with_csv(self, csv_path, root_path=None, recipient=None, user=None, load_all=False):
        """
        Reinitialize the manager with a new CSV file and optional context.
        
        Parameters:
        - csv_path (str): Path to the CSV file.
        - root_path (str, optional): Root path for context.
        - recipient (str, optional): Recipient name for context.
        - user (str, optional): User name for context.
        - load_all (bool, optional): If True, selects all rows in the DataFrame.
        """
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "File Error", "The specified CSV file does not exist.")
            return

        self.csv_path = csv_path
        if root_path:
            self.root_path = root_path
        if recipient:
            self.recipient = recipient
        if user:
            self.user = user

        try:
            # Reload the DeepEditor with the new file
            self.deep_editor.file_path = self.csv_path
            self.deep_editor.load_file()

            # Reset the headers and ID selection components
            self.id_header_dropdown.clear()
            self.id_value_list.clear()
            self.select_all_toggle.setChecked(False)
            self.load_headers()

            # Update the remapper with the new context
            self.remapper = StringRemapper(
                root_path=self.root_path,
                recipient=self.recipient,
                user=self.user,
                mappings_df=self.deep_editor.model.get_dataframe()
            )

            # Optionally load all rows
            if load_all:
                dataframe = self.deep_editor.model.get_dataframe()
                if dataframe is not None:
                    self.selected_rows_df = dataframe.copy()
                    self.selected_rows_updated.emit(self.selected_rows_df)  # Emit signal
                    self.display_selected_data()

            self.results_display.clear()

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load the CSV file: {str(e)}")

    def load_csv(self):
        """Load CSV data into the DeepEditor."""
        try:
            self.deep_editor.file_path = self.csv_path
            self.deep_editor.load_file()
            self.load_headers()
            QMessageBox.information(self, "Load Successful", "CSV file loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")

    def load_headers(self):
        """Load headers into the ID header dropdown."""
        try:
            dataframe = self.deep_editor.model.get_dataframe()
            if dataframe is not None:
                headers = list(dataframe.columns)
                self.id_header_dropdown.addItems(headers)
        except AttributeError:
            QMessageBox.critical(self, "Error", "Failed to load headers from the CSV file.")

    def toggle_all_id_values(self):
        """Select or deselect all ID values."""
        toggle_checked = self.select_all_toggle.isChecked()
        for index in range(self.id_value_list.count()):
            item = self.id_value_list.item(index)
            item.setSelected(toggle_checked)

    def populate_id_value_list(self):
        """Populate ID values based on the selected header."""
        self.id_value_list.clear()
        selected_header = self.id_header_dropdown.currentText()

        try:
            dataframe = self.deep_editor.model.get_dataframe()
            if dataframe is not None and selected_header:
                unique_values = dataframe[selected_header].dropna().unique()
                for value in unique_values:
                    self.id_value_list.addItem(QListWidgetItem(str(value)))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to populate ID values: {str(e)}")

    def set_selection(self):
        """Set selected rows into `selected_rows_df` and emit the signal."""
        try:
            dataframe = self.deep_editor.model.get_dataframe()
            selected_values = self.get_selected_id_values()
            selected_header = self.id_header_dropdown.currentText()

            if dataframe is not None and selected_header and selected_values:
                # Filter DataFrame by selected values
                self.selected_rows_df = dataframe[dataframe[selected_header].isin(selected_values)].copy()
                self.selected_rows_updated.emit(self.selected_rows_df)  # Emit signal
                self.display_selected_data()
            else:
                QMessageBox.warning(self, "Selection Error", "Ensure a header and values are selected.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set selection: {str(e)}")

    def get_selected_id_values(self):
        """Retrieve selected ID values."""
        return [item.text() for item in self.id_value_list.selectedItems()]

    def display_selected_data(self):
        """Display the current selected_rows_df in the results pane."""
        if self.selected_rows_df.empty:
            self.results_display.setText("No data selected.")
        else:
            self.results_display.setText(self.selected_rows_df.to_string(index=False))

    def clear_selected_data(self):
        """Clear selected rows DataFrame."""
        self.selected_rows_df = pd.DataFrame()
        self.results_display.setText("Selected rows cleared.")

    def finalize_logging(self):
        """Trigger logging of all final versions after remapping."""
        self.remapper.log_final_versions()

    def save_csv(self):
        """Save CSV data from DeepEditor."""
        if not self.csv_path:
            QMessageBox.warning(self, "Error", "No file path specified for saving.")
            return
        try:
            self.deep_editor.save_file()  # Calls DeepEditor to save CSV
            QMessageBox.information(self, "Save Successful", "CSV file saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    manager = StringMappingManager()
    manager.show()
    sys.exit(app.exec())