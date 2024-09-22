import sys
import zipfile
import os
import subprocess
import hashlib
import shutil
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox


class SaveExitWindow(QWidget):
    def __init__(self, zip_file):
        super().__init__()

        # Define the base .aufs path and consistent directories
        self.base_dir = os.path.expanduser("~/.aufs/osfsdirstoschema")
        self.working_dir = os.path.join(self.base_dir, "working")

        # Ensure the working directory exists
        os.makedirs(self.working_dir, exist_ok=True)

        # Use the zip file name to create a specific working directory inside the main working directory
        self.zip_file = zip_file
        self.schema_name = os.path.splitext(os.path.basename(zip_file))[0]
        self.schema_root = os.path.join(self.working_dir, self.schema_name)
        self.hash_file_path = os.path.join(self.working_dir, f"{self.schema_name}_tree.hash")

        # Setup window
        self.setWindowTitle(f"Save/Exit: {os.path.basename(zip_file)}")
        self.setGeometry(300, 300, 300, 250)  # Adjusted height for new button

        # Save button
        self.save_button = QPushButton("Save", self)
        self.save_button.setGeometry(50, 50, 200, 30)
        self.save_button.clicked.connect(self.save_schema)

        # Exit button
        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setGeometry(50, 90, 200, 30)
        self.exit_button.clicked.connect(self.exit_session)

        # Open Schema Root button (new functionality)
        self.open_root_button = QPushButton("Open Schema Root", self)
        self.open_root_button.setGeometry(50, 130, 200, 30)  # Positioned below the other buttons
        self.open_root_button.clicked.connect(self.open_schema_root)

        # Variable to track unsaved changes
        self.unsaved_changes = False

        # Unzip the schema into the working directory and save initial hash
        self.unzip_schema()

        # Check if the hash file exists; if not, save the initial hash
        if not os.path.exists(self.hash_file_path):
            self.initial_hash = self.save_directory_tree_hash()
        else:
            self.initial_hash = self.load_initial_hash()

    def unzip_schema(self):
        """
        Unzips the schema zip file into the working directory.
        """
        if not os.path.exists(self.schema_root):
            os.makedirs(self.schema_root, exist_ok=True)
            with zipfile.ZipFile(self.zip_file, 'r') as zip_ref:
                zip_ref.extractall(self.schema_root)
        else:
            print(f"{self.schema_root} already exists.")

    def save_directory_tree_hash(self):
        """
        Generate and save the current directory tree hash to a file.
        """
        dir_tree_hash = self.hash_directory_tree(self.schema_root)

        # Save the hash to a file in /working
        with open(self.hash_file_path, 'w') as f:
            f.write(dir_tree_hash)

        return dir_tree_hash

    def load_initial_hash(self):
        """
        Load the initial hash from the saved hash file.
        """
        with open(self.hash_file_path, 'r') as f:
            return f.read().strip()

    def hash_directory_tree(self, root):
        """
        Generate a hash for the directory tree rooted at 'root'.
        Only directories are considered, not files.
        """
        hash_obj = hashlib.sha256()
        for root_dir, dirs, _ in os.walk(root):
            for dir_name in dirs:
                # Compute the relative path of each directory and hash it
                rel_path = os.path.relpath(os.path.join(root_dir, dir_name), root)
                hash_obj.update(rel_path.encode('utf-8'))
        return hash_obj.hexdigest()

    def check_for_unsaved_changes(self):
        """
        Check if there are unsaved changes by comparing the current directory tree hash with the saved one.
        """
        current_hash = self.hash_directory_tree(self.schema_root)

        # Compare the hashes
        if current_hash != self.initial_hash:
            self.unsaved_changes = True
        else:
            self.unsaved_changes = False

    def save_schema(self):
        """
        Saves the current working directory into the schema zip file.
        """
        # Create a temporary zip file path
        temp_zip_path = os.path.join(self.working_dir, f"{self.schema_name}.zip")

        # Create the zip archive from the schema_root
        shutil.make_archive(temp_zip_path.replace(".zip", ""), 'zip', self.schema_root)

        # Move the temp zip to replace the existing one
        shutil.move(temp_zip_path, self.zip_file)

        # Save the updated directory tree hash
        self.initial_hash = self.save_directory_tree_hash()

        QMessageBox.information(self, "Save", "Schema saved successfully!")

    def cleanup_working_dir(self):
        """
        Remove the schema's working directory and the associated hash file.
        """
        # Remove the working directory for the schema
        if os.path.exists(self.schema_root):
            shutil.rmtree(self.schema_root)

        # Remove the hash file if it exists
        if os.path.exists(self.hash_file_path):
            os.remove(self.hash_file_path)

    def exit_session(self):
        """
        Exits the session. If there are unsaved changes, prompts the user to save.
        """
        self.check_for_unsaved_changes()

        if self.unsaved_changes:
            reply = QMessageBox.question(self, "Unsaved Changes", 
                                         "You have unsaved changes. Do you want to save before exiting?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_schema()
                self.cleanup_working_dir()
                self.close()
            elif reply == QMessageBox.No:
                self.cleanup_working_dir()
                self.close()
            # Cancel: do nothing, stay in the session
        else:
            self.cleanup_working_dir()
            self.close()

    def close_session(self):
        """ Close process for X or File -> Quit. Works like exit_session but separate. """
        self.check_for_unsaved_changes()
        if self.unsaved_changes:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "You have unsaved changes. Do you want to save before closing?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_schema()
                self.cleanup_working_dir()
                self.close()
            elif reply == QMessageBox.No:
                self.cleanup_working_dir()
                self.close()
            # Cancel does nothing
        else:
            self.cleanup_working_dir()
            self.close()

    def open_schema_root(self):
        """ Open the schema root directory in the system's file explorer """
        if sys.platform == 'win32':
            os.startfile(self.schema_root)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', self.schema_root])
        else:
            subprocess.Popen(['xdg-open', self.schema_root])


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # The first argument is the zip file passed from the main app
    zip_file = sys.argv[1]

    window = SaveExitWindow(zip_file)
    window.show()
    sys.exit(app.exec())
