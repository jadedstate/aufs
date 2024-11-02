import os
import sys
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QMessageBox, QLineEdit, QLabel, QFrame, QTextEdit, QFileDialog, QApplication)
from PySide6.QtCore import Qt

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.string_remapper import StringRemapper  # Ensure path is correct
from src.aufs.user_tools.packaging.string_mapping_manager import StringMappingManager  # Ensure path is correct
from src.aufs.user_tools.deep_editor import DeepEditor  # Assuming PopupEditor is a QWidget

class StringMappingManager(QWidget):
    def __init__(self, csv_path=None, parent=None):
        super().__init__(parent)
        self.csv_path = '/Users/uel/.aufs/config/jobs/active/primary_vfx/THRG2/fs_updates/fs_data-primary_vfx_THRG2-20241101T161851Z.csv'
        self.setWindowTitle(f"CSV Editor: {os.path.basename(csv_path) if csv_path else 'Untitled'}")
        self.resize(1000, 800)

        # Initialize DeepEditor with the loaded data
        button_flags = {'save': False, 'exit': False}
        self.deep_editor = DeepEditor(file_path=self.csv_path, button_flags=button_flags, file_type='csv', parent=self)

        # Main layout for CSV editor controls
        self.layout = QVBoxLayout(self)
        self.button_layout = QHBoxLayout()

        # CSV control buttons
        self.load_button = QPushButton("Load CSV")
        self.save_button = QPushButton("Save CSV")
        self.load_button.clicked.connect(self.load_csv)
        self.save_button.clicked.connect(self.save_csv)

        # Add buttons and editor to layout
        self.button_layout.addWidget(self.load_button)
        self.button_layout.addWidget(self.save_button)
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.deep_editor)

    def load_csv(self):
        """Prompt user to select a CSV file and load it into DeepEditor."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.csv_path = file_path
            try:
                self.deep_editor.file_path = self.csv_path
                self.deep_editor.load_file()
                QMessageBox.information(self, "Load Successful", "CSV file loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")

    def save_csv(self):
        """Save CSV data from DeepEditor."""
        if not self.csv_path:
            QMessageBox.warning(self, "Error", "No file path specified for saving.")
            return
        try:
            self.deep_editor.save_file()
            QMessageBox.information(self, "Save Successful", "CSV file saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV: {str(e)}")


class RemapInputUI(QWidget):
    def __init__(self, remapper_instance, parent=None):
        super().__init__(parent)
        self.remapper = remapper_instance
        self.setWindowTitle("CSV Remap Tool")
        self.resize(1800, 2000)

        # === Main Layout ===
        self.main_layout = QVBoxLayout(self)

        # === CSV Editor Section ===
        self.csv_editor = CSVEditor()
        self.main_layout.addWidget(self.csv_editor)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)

        # === Remapping Section ===
        remap_layout = QVBoxLayout()
        remap_layout.addWidget(QLabel("Remap Values"))

        # ID Header input
        remap_layout.addWidget(QLabel("Enter ID Header:"))
        self.id_header_input = QLineEdit()
        remap_layout.addWidget(self.id_header_input)

        # Button to show available headers
        self.show_headers_button = QPushButton("Show Available Headers")
        self.show_headers_button.clicked.connect(self.show_available_headers)
        remap_layout.addWidget(self.show_headers_button)

        # ID Value input
        remap_layout.addWidget(QLabel("Enter ID Value:"))
        self.id_value_input = QLineEdit()
        remap_layout.addWidget(self.id_value_input)

        # Target Columns input (comma-separated)
        remap_layout.addWidget(QLabel("Enter Target Columns to Remap (comma-separated):"))
        self.target_columns_input = QLineEdit()
        remap_layout.addWidget(self.target_columns_input)

        # Map Values button
        self.map_button = QPushButton("Map Values")
        self.map_button.clicked.connect(self.map_values)
        remap_layout.addWidget(self.map_button)

        # Results display area
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        remap_layout.addWidget(QLabel("Mapping Results:"))
        remap_layout.addWidget(self.results_display)

        # Add remapping layout to main layout
        self.main_layout.addLayout(remap_layout)

        self.setLayout(self.main_layout)

    def show_available_headers(self):
        """Show a popup with available headers from the CSV."""
        headers = list(self.csv_editor.deep_editor.model.get_dataframe().columns)
        headers_popup = QMessageBox(self)
        headers_popup.setWindowTitle("Available Headers")
        headers_popup.setText("Available Headers:\n" + "\n".join(headers))
        headers_popup.exec()

    def map_values(self):
        """Perform the remap and display results based on user inputs."""
        id_header = self.id_header_input.text().strip()
        id_value = self.id_value_input.text().strip()
        target_columns = [col.strip() for col in self.target_columns_input.text().split(",")]

        if not id_header or not id_value or not target_columns:
            QMessageBox.warning(self, "Input Error", "Please fill in all fields.")
            return

        # Perform remapping and display results
        try:
            result = self.remapper.remap(id_header, id_value, target_columns)
            self.display_results(result)
        except Exception as e:
            QMessageBox.critical(self, "Remap Error", f"Failed to remap values: {str(e)}")

    def display_results(self, results):
        """Display the remapping results in the text area."""
        if not results:
            self.results_display.setText("No mapping found for the given inputs.")
        else:
            result_text = "\n".join([f"{col}: {value}" for col, value in results])
            self.results_display.setText(result_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    remapper_instance = StringRemapper(None)  # Replace `None` with actual DataFrame when available
    window = RemapInputUI(remapper_instance=remapper_instance)
    window.show()
    sys.exit(app.exec())
