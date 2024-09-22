import sys
import os
import zipfile
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, QListWidgetItem, QListWidget, QVBoxLayout, QWidget,
                               QMessageBox)
from PySide6.QtCore import Qt, QObject, Signal
import subprocess
from pathlib import Path

class OSFSToSchemaApp(QMainWindow):
    schema_passed = Signal(str)  # Signal to pass the schema path to the Wrangler

    def __init__(self):
        super().__init__()

        # Ensure ~/.aufs/osfsdirstoschema and subdirectories exist
        self.setup_aufs_directories()

        # Setup the window
        self.setWindowTitle("OSFSdirs-Schema to PARQUET")
        self.setGeometry(300, 300, 400, 300)

        # Main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add buttons
        self.open_button = QPushButton("Open", self)
        self.validate_button = QPushButton("Validate", self)
        self.pass_to_wrangler_button = QPushButton("Pass to Wrangler", self)
        layout.addWidget(self.open_button)
        layout.addWidget(self.validate_button)
        layout.addWidget(self.pass_to_wrangler_button)

        self.open_button.clicked.connect(self.open_existing)
        self.validate_button.clicked.connect(self.validate_schema)
        self.pass_to_wrangler_button.clicked.connect(self.pass_to_wrangler)

        # Add the list widget for schema files, this will expand vertically on resize
        self.schema_list = QListWidget(self)
        layout.addWidget(self.schema_list, stretch=1)  # Stretch factor for the list widget to expand vertically

        # Add refresh button for the schema list
        self.refresh_button = QPushButton("Refresh List", self)
        layout.addWidget(self.refresh_button)

        self.refresh_button.clicked.connect(self.refresh_schema_list)

        # Populate schema list on startup
        self.refresh_schema_list()

    def pass_to_wrangler(self):
        """
        Pass the selected schema to the Wrangler for further processing.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            schema_file = selected_item.text().replace(" (In Progress)", "")
            schema_path = os.path.join(self.saved_dir, schema_file)

            # Emit the signal to pass the schema path to the Wrangler
            self.schema_passed.emit(schema_path)

            print(f"Passing schema {schema_file} to Wrangler...")
            QMessageBox.information(self, "Wrangler", f"Schema {schema_file} passed to Wrangler!")
            
    def setup_aufs_directories(self):
        """
        Ensures that the ~/.aufs/osfsdirstoschema directory structure is in place.
        """
        home_dir = str(Path.home())
        self.aufs_root = os.path.join(home_dir, '.aufs', 'osfsdirstoschema')
        self.working_dir = os.path.join(self.aufs_root, 'working')
        self.saved_dir = os.path.join(self.aufs_root, 'saved')

        os.makedirs(self.working_dir, exist_ok=True)
        os.makedirs(self.saved_dir, exist_ok=True)

    def refresh_schema_list(self):
        """
        Refreshes the list of schemas, greying out the ones that are currently open.
        """
        self.schema_list.clear()

        # List all saved schemas
        for schema_file in os.listdir(self.saved_dir):
            if schema_file.endswith('.zip'):
                item_text = schema_file
                working_path = os.path.join(self.working_dir, schema_file.replace('.zip', ''))

                item = QListWidgetItem(item_text)

                if os.path.exists(working_path):
                    item.setFlags(Qt.NoItemFlags)  # Grey out the item
                    item.setText(f"{item_text} (In Progress)")

                self.schema_list.addItem(item)

    def open_existing(self):
        """
        Opens an existing schema from the ~/.aufs/osfsdirstoschema/saved directory.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            zip_file = selected_item.text().replace(" (In Progress)", "")
            self.start_subprocess(os.path.join(self.saved_dir, zip_file))

    def validate_schema(self):
        """
        Validate the schema.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            schema_file = selected_item.text().replace(" (In Progress)", "")
            schema_path = os.path.join(self.saved_dir, schema_file)

            # Validation logic placeholder - you can replace with actual validation
            print(f"Validating schema: {schema_path}")
            QMessageBox.information(self, "Validation", f"Schema {schema_file} validated successfully!")

    def pass_to_wrangler(self):
        """
        Pass the selected schema to the Wrangler for further processing.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            schema_file = selected_item.text().replace(" (In Progress)", "")
            schema_path = os.path.join(self.saved_dir, schema_file)

            # Pass to Wrangler logic placeholder - you can replace with actual logic
            print(f"Passing schema {schema_file} to Wrangler...")
            QMessageBox.information(self, "Wrangler", f"Schema {schema_file} passed to Wrangler!")

    def start_subprocess(self, zip_file):
        """
        Starts a subprocess for editing the schema.
        """
        current_dir = os.path.dirname(__file__)
        sp_script_path = os.path.join(current_dir, 'os_fs_dirs_to_schema_sp.py')
        python_interpreter = sys.executable
        # Start the subprocess using the full script path
        subprocess.Popen([python_interpreter, sp_script_path, zip_file], start_new_session=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OSFSToSchemaApp()
    window.show()
    sys.exit(app.exec())
