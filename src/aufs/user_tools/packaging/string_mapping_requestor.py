import os
import sys
import re
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QMessageBox, QLineEdit, QLabel, QTextEdit, QFileDialog, QMenu,
                               QApplication, QComboBox, QListWidget, QListWidgetItem, QToolButton, QStyle, QTabWidget)
from PySide6.QtCore import Qt

# Add source directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.string_mapping_manager import StringMappingManager

class OutputManager:
    def __init__(self):
        self.format_handlers = {
            'csv': self._write_csv,
            'txt': self._write_txt,
            # Additional formats can be added here
        }
        self.naming_conventions = {
            'original': self._original_name,
            'save_as': self._save_as_name,
            'timestamped': self._timestamped_name,
            # New conventions can be added here
        }

    def save(self, data, file_path, format_type, naming_option):
        # Get the correct file path based on the naming option
        save_path = self.naming_conventions[naming_option](file_path)

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
        return save_path if save_path else file_path  # Return chosen path or original if canceled

    def _timestamped_name(self, file_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        return f"{base}_{timestamp}{ext}"

    # Format-specific writing methods
    def _write_csv(self, data, save_path):
        if isinstance(data, str):  # Assume string data is newline-separated for CSV
            pd.DataFrame({'Remapped_Text': data.split("\n")}).to_csv(save_path, index=False)

    def _write_txt(self, data, save_path):
        with open(save_path, 'w') as f:
            f.write(data)

    # Additional methods for other formats can be defined here

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
        return Parsers.extract_uppercase(chunk) if parse_type == "uppercase" else Parsers.extract_paths(chunk)

class Parsers:
    @staticmethod
    def extract_uppercase(chunk, delimiters=None):
        print("CHUNK provided by the PayloadHandler is:")
        print(chunk)
        
        # Default delimiters if none provided
        delimiters = delimiters or ['-', '_', '.', '/']
        
        # Split based on any delimiter, then filter for uppercase matches
        parts = re.split(f"[{''.join(map(re.escape, delimiters))}]", chunk)
        
        # Keep only parts that are fully uppercase or meet specific uppercase conditions
        parsed_strings = [part for part in parts if part.isupper() and len(part) > 1]

        print("PARSED STRINGS are:", parsed_strings)  # Single debug output
        return parsed_strings

    @staticmethod
    def extract_paths(chunk):
        print(chunk)
        path_suspects = []
        i = 0
        while i < len(chunk):
            # Check for / or \ as possible path indicators
            if chunk[i] in ('/', '\\'):
                # Determine start of path
                # If there's a Windows drive letter pattern (e.g., "C:"), set the start 2 chars back
                start = i - 2 if i >= 2 and re.match(r'[A-Za-z]:', chunk[i-2:i]) else i
                
                # Search forwards from the current position until a terminating character is found
                end = i
                while end < len(chunk) and chunk[end] not in (' ', '\n', '\t', ';', ',', '|'):
                    end += 1
                
                # Extract path suspect from 'start' to 'end', excluding the 'out' point (terminator)
                path_suspect = chunk[start:end]
                path_suspects.append(path_suspect)
                
                # Move the index to the end of the current path to continue scanning
                i = end
            else:
                i += 1

        # First-pass filtering (none for now, just return all suspects)
        return path_suspects

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
        self.tabs.addTab(self.manager_tab, "String Mapping Manager")
        
        # === Requestor Tab ===
        self.requestor_tab = QWidget()
        self.requestor_layout = QVBoxLayout(self.requestor_tab)
        self.setup_requestor_ui(self.requestor_layout)
        self.tabs.addTab(self.requestor_tab, "Requestor Interface")

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

        # === Remap Type ===
        remap_type_layout = QHBoxLayout()
        self.remap_type_combo = QComboBox()
        self.remap_type_combo.addItems(["uppercase", "path"])
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
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)")
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

        # Determine selected columns for remapping in CSV files
        selected_columns = []
        if self.file_type == 'csv':
            for i in range(self.column_list_widget.count()):
                item = self.column_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_columns.append(item.text())
            if "all-cols" in selected_columns:
                selected_columns = self.preview_data.columns.tolist()

        # Get remap type from the combo box to select the appropriate parser
        parse_type = self.remap_type_combo.currentText().lower()  # "uppercase" or "path"
        self.preview_display.clear()
        remapped_texts = []

        # Process each chunk using PayloadHandler
        for chunk in self.payload_handler.chunk_data(self.preview_data, selected_columns):
            # Use the parse_type to determine which parser method to call
            parsed_strings = self.payload_handler.parse(chunk, parse_type)

            # Initialize remapped chunk to be modified in place
            remapped_chunk = chunk

            # Retrieve mappings for each parsed string from manager
            if parsed_strings:
                mappings = self.manager.map_requested_values(id_header, id_value, parsed_strings)

                # Filter out mappings where the replacement value is not a non-empty string
                valid_mappings = [(existing_value, replacement_value) 
                                for existing_value, replacement_value in mappings 
                                if isinstance(replacement_value, str) and replacement_value.strip()]

                # Apply valid mappings to the chunk
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    coordinator = RequestorUI()
    coordinator.show()
    sys.exit(app.exec())
