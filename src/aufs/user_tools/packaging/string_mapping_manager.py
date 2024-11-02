import os
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QMessageBox, QLineEdit, QLabel, QFrame, QTextEdit, QFileDialog, QApplication)
from PySide6.QtCore import Qt

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.deep_editor import DeepEditor  # The CSV editor component
from src.aufs.user_tools.packaging.string_remapper import StringRemapper  # The remapping logic class

class StringMappingManager(QWidget):
    def __init__(self, csv_path=None, parent=None):
        super().__init__(parent)
        self.csv_path = '/Users/uel/.aufs/config/jobs/active/primary_vfx/THRG2/fs_updates/fs_data-primary_vfx_THRG2-20241101T161851Z.csv'
        self.setWindowTitle(f"CSV and Remap Tool: {os.path.basename(self.csv_path) if self.csv_path else 'Untitled'}")
        self.resize(1000, 900)

        # Initialize the remapper instance without the DataFrame (we’ll set it after loading CSV)
        self.remapper = StringRemapper()

        # Main layout
        self.main_layout = QVBoxLayout(self)

        # === CSV Editing Section ===
        # Initialize DeepEditor for CSV editing
        self.button_flags = {'save': False, 'exit': False}
        self.deep_editor = DeepEditor(file_path=self.csv_path, button_flags=self.button_flags, file_type='csv', parent=self)

        # Button layout for CSV controls
        csv_button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load CSV")
        self.save_button = QPushButton("Save CSV")
        self.load_button.clicked.connect(self.load_csv)
        self.save_button.clicked.connect(self.save_csv)
        csv_button_layout.addWidget(self.load_button)
        csv_button_layout.addWidget(self.save_button)

        # Add CSV editor and buttons to layout
        self.main_layout.addLayout(csv_button_layout)
        self.main_layout.addWidget(self.deep_editor)

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
        self.id_header_input.setText('FILE')
        remap_layout.addWidget(self.id_header_input)

        # Button to show available headers
        self.show_headers_button = QPushButton("Show Available Headers")
        self.show_headers_button.clicked.connect(self.show_available_headers)
        remap_layout.addWidget(self.show_headers_button)

        # ID Value input
        remap_layout.addWidget(QLabel("Enter ID Value:"))
        self.id_value_input = QLineEdit()
        self.id_value_input.setText('/Users/uel/Desktop/old_screenshots/Screenshot 2024-05-07 at 20.22.%02d.jpeg')
        remap_layout.addWidget(self.id_value_input)

        # Target Columns input (comma-separated list)
        remap_layout.addWidget(QLabel("Enter Target Columns to Remap (comma-separated):"))
        self.target_columns_input = QLineEdit()
        self.target_columns_input.setText('STATUS, SEQUENCENAME')
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

    def load_csv(self):
        """Load CSV data into DeepEditor without setting mappings in StringRemapper."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.csv_path = file_path  # Update self.csv_path with the selected file
            try:
                self.deep_editor.file_path = self.csv_path  # Update DeepEditor with the new file path
                self.deep_editor.load_file()  # Load the CSV file in DeepEditor

                QMessageBox.information(self, "Load Successful", "CSV file loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")
        else:
            QMessageBox.information(self, "No File Selected", "No file was selected for loading.")

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

    def show_available_headers(self):
        """Show a popup with available headers from the CSV."""
        headers = list(self.deep_editor.model.get_dataframe().columns)
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

        # Fetch the latest mappings DataFrame from DeepEditor and set it in StringRemapper
        mappings_df = self.deep_editor.model.get_dataframe()
        if mappings_df is not None:
            self.remapper.set_mappings(mappings_df)
        else:
            QMessageBox.critical(self, "Error", "Failed to retrieve mappings DataFrame.")
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
    manager = StringMappingManager()
    manager.show()
    sys.exit(app.exec())