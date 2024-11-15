# src/aufs/user_tools/packaging/string_mapping_requestor.py

import os
import sys
import re
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QMessageBox, QLineEdit, QLabel, QTextEdit, QFileDialog, QMenu,
                               QApplication, QComboBox, QListWidget, QListWidgetItem, QToolButton, QStyle, QTabWidget)
from PySide6.QtCore import Qt

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.string_mapping_manager import StringMappingManager

class OutputManager:
    def __init__(self):
        self.format_handlers = {
            'csv': self._write_csv,
            'txt': self._write_txt,
        }
        self.naming_conventions = {
            'original': self._original_name,
            'save_as': self._save_as_name,
            'timestamped': self._timestamped_name,
        }

    def save(self, data, file_path, format_type, naming_option):
        # Get the correct file path based on the naming option
        save_path = self.naming_conventions[naming_option](file_path)

        # Check if the save path is empty (indicating cancel)
        if not save_path:
            QMessageBox.information(None, "Canceled", "Save operation was canceled.")
            return

        # Call the appropriate format handler method
        if format_type in self.format_handlers:
            self.format_handlers[format_type](data, save_path)
            QMessageBox.information(None, "Success", f"File saved successfully as:\n{save_path}")
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    # Naming convention methods
    def _original_name(self, file_path):
        return file_path

    def _save_as_name(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(None, "Save As", file_path, "All Files (*)")
        return save_path  # Directly return the selected or empty path (if canceled)

    def _timestamped_name(self, file_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        return f"{base}_{timestamp}{ext}"

    # Format-specific writing methods
    def _write_csv(self, data, save_path):
        if isinstance(data, str):
            pd.DataFrame({'Remapped_Text': data.split("\n")}).to_csv(save_path, index=False)

    def _write_txt(self, data, save_path):
        with open(save_path, 'w') as f:
            f.write(data)

class FileIO:
    def read(self, file_path):
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        else:
            with open(file_path, 'r') as f:
                text = f.read()
            return pd.DataFrame([[text]], columns=['text'])

    def write(self, data, save_path):
        if isinstance(data, pd.DataFrame):
            data.to_csv(save_path, index=False)
        else:
            with open(save_path, 'w') as f:
                f.write(data)

class PayloadHandler:
    def chunk_data(self, data, columns=None):
        if isinstance(data, pd.DataFrame):
            # Select specified columns, or use all columns if none are specified
            data = data[columns] if columns else data
            for _, row in data.iterrows():
                # Yield each field as a full string without using to_string()
                yield " ".join(str(value) for value in row.values)
        else:
            # Handle plain text data for non-CSV files
            yield data

    def reintegrate(self, processed_chunks, data):
        return pd.DataFrame(processed_chunks) if isinstance(data, pd.DataFrame) else "\n".join(processed_chunks)

    def parse(self, chunk, parse_type):
        """Route to the appropriate parser based on the parse_type."""
        if parse_type == "uppercase":
            return Parsers.extract_uppercase(chunk)
        elif parse_type == "path":
            return Parsers.extract_paths(chunk)
        elif parse_type == "raw_item_name":
            return Parsers.extract_raw_item_names(chunk)  # New functionality for raw_item_name
        else:
            raise ValueError(f"Unknown parse_type: {parse_type}")

class Parsers:
    @staticmethod
    def filter_blacklist_chars(parsed_list, blacklist_chars=None):
        """Filter out elements from parsed_list that contain any blacklisted character.
        
        If no blacklist_chars list is provided, a default set of characters will be used.
        """
        if blacklist_chars is None:
            blacklist_chars = ['>', '<', '|', ';']  # Default characters

        # Filter out items containing any blacklisted character
        filtered_list = [
            item for item in parsed_list
            if not any(char in item for char in blacklist_chars)
        ]
        
        return filtered_list

    @staticmethod
    def extract_paths(chunk, blacklist_chars=None):
        """Extracts potential path strings from the provided chunk and filters them
        using the blacklist if provided.
        """
        path_suspects = []
        i = 0
        while i < len(chunk):
            if chunk[i] in ('/', '\\'):
                start = i - 2 if i >= 2 and re.match(r'[A-Za-z]:', chunk[i-2:i]) else i
                end = i
                while end < len(chunk) and chunk[end] not in (' ', '\n', '\t', ';', ',', '|'):
                    end += 1
                path_suspect = chunk[start:end]
                path_suspects.append(path_suspect)
                i = end
            else:
                i += 1
        
        # Apply blacklist filtering if any suspects were found
        return Parsers.filter_blacklist_chars(path_suspects, blacklist_chars)

    @staticmethod
    def extract_uppercase(chunk, delimiters=None):
        # print("CHUNK provided by the PayloadHandler is:", chunk)
        delimiters = delimiters or ['-', '_', '.', '/', ':', '\\']
        parts = re.split(f"[{''.join(map(re.escape, delimiters))}]", chunk)
        parsed_strings = [part for part in parts if part.isupper() and len(part) > 1]
        # print("PARSED STRINGS are:", parsed_strings)
        return parsed_strings

    @staticmethod
    def extract_raw_item_names(chunk):
        """Extract paths that end with a file extension."""
        path_suspects = Parsers.extract_paths(chunk)
        filtered_suspects = [
            path for path in path_suspects if re.search(r'\.\w+$', path)  # Basic check for file extension
        ]
        # print("raw filenames with file extensions:", filtered_suspects)
        raw_items = [(path, path.split('/')[-1]) for path in filtered_suspects]
        # print("RAWITEMNAMES are: ", raw_items)
        return raw_items

class MappingRequestor:
    def __init__(self):
        self.string_mapper = StringMappingManager()

    def map(self, parsed_strings, id_header, id_value, target_columns):
        self.string_mapper.set_mapping_context(id_header, id_value, target_columns)
        return [self.string_mapper.map_requested_values(string) for string in parsed_strings]

class RequestorUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("String Mapping Workflow")
        self.resize(1000, 900)

        self.file_io = FileIO()
        self.payload_handler = PayloadHandler()
        self.mapping_requestor = MappingRequestor()
        self.manager = StringMappingManager()  # Assuming this has a QWidget-based UI component
        self.output_manager = OutputManager()
        self.preview_data = None

        # Create tab widget
        self.tabs = QTabWidget(self)
        
        # === String Mapping Manager Tab ===
        self.manager_tab = QWidget()
        self.manager_layout = QVBoxLayout(self.manager_tab)
        self.manager_layout.addWidget(self.manager)  # Assuming this is a QWidget
        
        # === Requestor Tab ===
        self.requestor_tab = QWidget()
        self.requestor_layout = QVBoxLayout(self.requestor_tab)
        self.setup_requestor_ui(self.requestor_layout)
        self.tabs.addTab(self.requestor_tab, "Requestor Interface")
        self.tabs.addTab(self.manager_tab, "String Mapping Manager")

        # Add tabs to main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def setup_requestor_ui(self, layout):
        """Sets up the main Requestor UI components within the given layout."""
        
        # === File Loading ===
        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.load_button = QPushButton("Load File")
        self.load_button.clicked.connect(self.load_file)
        file_layout.addWidget(QLabel("File Path:"))
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(self.load_button)
        layout.addLayout(file_layout)

        # In the setup_requestor_ui method
        remap_type_layout = QHBoxLayout()
        self.remap_type_combo = QComboBox()

        # Display names with corresponding parse types in a dictionary
        """
        For uppercase - we use a single row from the csv loaded in the manager to replace all the vars in the csv loaded in the requestor. we must have
        the concept of adding to a package in place. the requestor needs to have 'open' and 'closed' remapping sessions.
        we must be able to save and load 'open' ones
        we need to be able to select rows in the manager's csv
        For raw_item_name - we use every row in the csv loaded in the manager to replace all the paths found in the file loaded in the requestor.
        """
        self.remap_type_options = {
            "Uppercase Variables, no curly brackets": "uppercase",
            "Raw Item-names - remap paths": "raw_item_name"
        }

        # Populate the combo box with display names
        self.remap_type_combo.addItems(self.remap_type_options.keys())
        remap_type_layout.addWidget(QLabel("Remap Type:"))
        remap_type_layout.addWidget(self.remap_type_combo)
        layout.addLayout(remap_type_layout)


        # === Column Selection for CSV ===
        self.column_list_widget = QListWidget()
        self.column_list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.column_list_widget.setVisible(False)
        layout.addWidget(QLabel("Select Columns to Work On:"))
        layout.addWidget(self.column_list_widget)

        # === Preview Display ===
        self.preview_display = QTextEdit()
        self.preview_display.setReadOnly(True)
        layout.addWidget(QLabel("Preview of Remapped Data:"))
        layout.addWidget(self.preview_display)

        # === Process Button ===
        self.remap_button = QPushButton("Process and Preview Remap")
        self.remap_button.clicked.connect(self.process_remap)
        layout.addWidget(self.remap_button)

        # === Save Button with Dropdown Menu ===
        save_button_layout = QHBoxLayout()
        self.save_button = QToolButton(self)
        self.save_button.setText("Save")
        self.save_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.save_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.save_button.setFixedWidth(150)

        # Create a dropdown menu for additional save options
        save_menu = QMenu(self)
        save_as_action = save_menu.addAction("Save As")
        timestamped_action = save_menu.addAction("Save with Timestamp")
        self.save_button.setMenu(save_menu)

        # Connect save button and menu actions
        self.save_button.clicked.connect(lambda: self.save_remapped_file("original"))
        save_as_action.triggered.connect(lambda: self.save_remapped_file("save_as"))
        timestamped_action.triggered.connect(lambda: self.save_remapped_file("timestamped"))

        save_button_layout.addWidget(self.save_button)
        layout.addLayout(save_button_layout)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt);;CSV Files (*.csv)")
        if file_path:
            self.file_path_input.setText(file_path)
            self.file_type = 'csv' if file_path.endswith('.csv') else 'txt'
            if self.file_type == 'csv':
                self.preview_data = pd.read_csv(file_path)
                self.column_list_widget.clear()
                self.column_list_widget.setVisible(True)
                all_cols_item = QListWidgetItem("all-cols")
                all_cols_item.setCheckState(Qt.Unchecked)
                self.column_list_widget.addItem(all_cols_item)
                for col in self.preview_data.columns:
                    item = QListWidgetItem(col)
                    item.setCheckState(Qt.Unchecked)
                    self.column_list_widget.addItem(item)
            else:
                with open(file_path, 'r') as file:
                    text = file.read()
                self.preview_data = pd.DataFrame([[text]], columns=['text'])
                self.column_list_widget.setVisible(False)
            self.preview_display.setText(str(self.preview_data))

    def process_remap(self):
        if self.preview_data is None:
            QMessageBox.warning(self, "Warning", "Please load a file to process.")
            return

        # Retrieve ID header, ID value, and parse type from UI inputs
        id_header = self.manager.id_header_input.text().strip()
        id_value = self.manager.id_value_input.text().strip()

        # Retrieve parse_type using the selected display name
        displayed_parse_type = self.remap_type_combo.currentText()
        parse_type = self.remap_type_options.get(displayed_parse_type)

        
        self.preview_display.clear()
        remapped_texts = []

        # Determine selected columns for remapping in CSV files
        selected_columns = []
        if self.file_type == 'csv':
            for i in range(self.column_list_widget.count()):
                item = self.column_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_columns.append(item.text())
            if "all-cols" in selected_columns:
                selected_columns = self.preview_data.columns.tolist()

        # Set a flag for handling raw filenames
        is_raw_item_name = (parse_type == "raw_item_name")

        # Process each chunk using PayloadHandler
        for chunk in self.payload_handler.chunk_data(self.preview_data, selected_columns):
            # Use the parse_type to determine which parser method to call
            parsed_strings = self.payload_handler.parse(chunk, parse_type)

            # Initialize remapped chunk to be modified in place
            remapped_chunk = chunk

            if is_raw_item_name:
                # For raw_item_name, use (path_suspect, to_find) tuples for mapping
                for path_suspect, to_find in parsed_strings:
                    # Perform mapping with custom ID header, value, and target for raw_item_name
                    print(path_suspect)
                    mappings = self.manager.map_requested_values("RAWITEMNAME", to_find, ["FILE"]) or []
                    print("rawitemname mappings ARE: ", mappings)

                    # Filter mappings for valid (non-empty) replacement values
                    valid_mappings = [
                        (existing_value, replacement_value) for existing_value, replacement_value in mappings
                        if isinstance(replacement_value, str) and replacement_value.strip()
                    ]

                    # Replace path_suspect in remapped_chunk with the replacement value
                    for existing_value, replacement_value in valid_mappings:
                        remapped_chunk = remapped_chunk.replace(path_suspect, replacement_value)

            else:
                # For other parse types ("uppercase", "path"), continue as before
                mappings = self.manager.map_requested_values(id_header, id_value, parsed_strings) or []

                # Apply valid mappings to the chunk
                valid_mappings = [
                    (existing_value, replacement_value) for existing_value, replacement_value in mappings
                    if isinstance(replacement_value, str) and replacement_value.strip()
                ]
                for existing_value, replacement_value in valid_mappings:
                    remapped_chunk = remapped_chunk.replace(existing_value, replacement_value)

            # Append remapped chunk to the list for preview display
            remapped_texts.append(remapped_chunk)

        # Update preview display with remapped content
        self.preview_display.setText("\n".join(remapped_texts))

    def save_remapped_file(self, save_option):
        """Save the remapped data based on selected save options."""
        file_path = self.file_path_input.text()
        format_type = 'csv' if file_path.endswith('.csv') else 'txt'
        remapped_data = self.preview_display.toPlainText()

        # Call OutputManager to handle the save operation
        self.output_manager.save(remapped_data, file_path, format_type, save_option)
        
        # Trigger final version logging in StringMappingManager
        self.manager.finalize_logging()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    coordinator = RequestorUI()
    coordinator.show()
    sys.exit(app.exec())