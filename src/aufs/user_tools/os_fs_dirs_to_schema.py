import sys
import os
import zipfile
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, QListWidgetItem, QListWidget, QVBoxLayout, QWidget,
                               QMessageBox)
from PySide6.QtCore import Qt, QEvent
import subprocess
from pathlib import Path
from scraper import DirectoryScraper

class OSFSToSchemaApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Ensure ~/.aufs/osfsdirstoschema and subdirectories exist
        self.setup_aufs_directories()

        # Setup the window
        self.setWindowTitle("OSFS Dirs to Schema Tool")
        self.setGeometry(300, 300, 400, 300)

        # Main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add buttons
        self.open_button = QPushButton("Open existing", self)
        self.new_button = QPushButton("Start from nothing", self)
        self.template_button = QPushButton("Get template to start", self)
        layout.addWidget(self.open_button)
        layout.addWidget(self.new_button)
        layout.addWidget(self.template_button)

        self.open_button.clicked.connect(self.open_existing)
        self.new_button.clicked.connect(self.start_from_nothing)
        self.template_button.clicked.connect(self.get_template_to_start)

        # Add the list widget for schema files, this will expand vertically on resize
        self.schema_list = QListWidget(self)
        layout.addWidget(self.schema_list, stretch=1)  # Stretch factor for the list widget to expand vertically

        # Add refresh button for the schema list
        self.refresh_button = QPushButton("Refresh List", self)
        layout.addWidget(self.refresh_button)

        self.refresh_button.clicked.connect(self.refresh_schema_list)

        # Populate schema list on startup
        self.refresh_schema_list()

    def closeEvent(self, event):
        """
        Override close event to handle cleanup when window is closed
        (includes OS window controls and File->Quit).
        """
        self.cleanup_and_exit()
        
    def cleanup_and_exit(self):
        """
        Add cleanup logic here.
        """
        print("Performing cleanup before exit...")
        # Add any other cleanup code you need here

        self.close()  # Make sure the window is closed

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

    def start_from_nothing(self):
        """
        Starts from a blank schema.
        """
        zip_file, _ = QFileDialog.getSaveFileName(self, "Create New Schema", self.saved_dir, "Zip Files (*.zip)")
        if zip_file:
            # Create an empty zip file
            with zipfile.ZipFile(zip_file, 'w') as zipf:
                pass
            self.start_subprocess(zip_file)

    def get_template_to_start(self):
        """
        Uses the DirectoryScraper to create a template from the filesystem.
        """
        root_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Scrape")
        if root_dir:
            # Get the schema name from the user via a save dialog
            zip_file, _ = QFileDialog.getSaveFileName(self, "Save Template as Zip", self.saved_dir, "Zip Files (*.zip)")
            if zip_file:
                # Extract the source directory name and schema name
                source_dirname = os.path.basename(root_dir).replace(' ', '_')  # Ensure safe name
                schema_name = os.path.splitext(os.path.basename(zip_file))[0].replace(' ', '_')

                # Construct the unique replica directory name using the source dirname and schema name
                temp_replica_root = os.path.join(os.path.dirname(zip_file), f"{source_dirname}-replica-{schema_name}")
                
                # Ensure a fresh directory for the replica
                os.makedirs(temp_replica_root, exist_ok=True)

                scraper = DirectoryScraper()
                dirs = scraper.scrape_directories(root_dir)
                scraper.create_replica(dirs, temp_replica_root, root_dir)
                
                # Zip the replica
                scraper.zip_replica(temp_replica_root, zip_file)

                # Start the subprocess with the newly created zip file
                self.start_subprocess(zip_file)

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
