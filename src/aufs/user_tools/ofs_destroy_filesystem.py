import platform
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, 
                               QTextEdit, QMessageBox, QProgressDialog)
from PySide6.QtCore import Qt

class DestroyFilesystemUtility(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ObjectiveFS Destroy Filesystem Utility")
        self.setGeometry(100, 100, 800, 600)
        self.env_dir = None  # Directory containing environment variables

        # Main layout
        main_layout = QVBoxLayout(self)

        # Environment Directory Selection
        env_layout = QHBoxLayout()
        env_label = QLabel("Env Directory:")
        self.env_dir_display = QLabel("Not set")
        self.load_env_button = QPushButton("Load Env Directory")
        self.load_env_button.clicked.connect(self.load_env_directory)
        env_layout.addWidget(env_label)
        env_layout.addWidget(self.env_dir_display)
        env_layout.addWidget(self.load_env_button)
        main_layout.addLayout(env_layout)

        # Filesystem List and Reload Button
        fs_layout = QHBoxLayout()
        fs_layout.addWidget(QLabel("Available Filesystems"))
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.populate_filesystem_list)
        fs_layout.addWidget(self.reload_button)
        main_layout.addLayout(fs_layout)
        
        self.filesystem_list = QListWidget()
        main_layout.addWidget(self.filesystem_list)

        # Destroy Filesystem Button
        self.destroy_button = QPushButton("Destroy Selected Filesystem")
        self.destroy_button.clicked.connect(self.initiate_destroy)
        self.destroy_button.setEnabled(False)
        main_layout.addWidget(self.destroy_button)

        # Output Pane
        self.output_pane = QTextEdit()
        self.output_pane.setReadOnly(True)
        main_layout.addWidget(QLabel("Process Output:"))
        main_layout.addWidget(self.output_pane)

    def load_env_directory(self):
        """Load the environment directory, populate filesystem list."""
        from PySide6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(self, "Select Env Directory")
        if directory:
            self.env_dir = directory
            self.env_dir_display.setText(directory)
            self.populate_filesystem_list()

    def populate_filesystem_list(self):
        """Retrieve and display available filesystems."""
        self.filesystem_list.clear()
        command = f"OBJECTIVEFS_ENV={self.env_dir} mount.objectivefs list -a"
        output = self.run_command(command)

        if output:
            filesystems = self.parse_filesystems(output)
            for fs in filesystems:
                item = QListWidgetItem(fs)
                self.filesystem_list.addItem(item)
            self.output_pane.append("Filesystems loaded successfully.\n")
            self.destroy_button.setEnabled(True)
        else:
            self.output_pane.append("Failed to load filesystems.\n")
            self.destroy_button.setEnabled(False)

    def parse_filesystems(self, output):
        """Parse output from the filesystem list command."""
        lines = output.splitlines()
        filesystems = []
        for line in lines:
            if line.startswith("wasabi://") or line.startswith("s3://"):
                fs_name = line.split()[0]
                filesystems.append(fs_name)
        return filesystems

    def initiate_destroy(self):
        """Initiate the destruction process with confirmation and feedback."""
        selected_items = self.filesystem_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Destroy Filesystem", "Please select a filesystem to destroy.")
            return

        filesystem_name = selected_items[0].text()
        confirmation = QMessageBox.question(
            self, "Confirm Destruction",
            f"Are you sure you want to destroy the filesystem '{filesystem_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmation != QMessageBox.Yes:
            self.output_pane.append("Filesystem destruction canceled.\n")
            return

        progress_dialog = QProgressDialog(f"Destroying filesystem '{filesystem_name}'...", "Cancel", 0, 1, self)
        progress_dialog.setWindowTitle("Filesystem Destruction Progress")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.show()

        # Run the destroy command
        command = f"sudo OBJECTIVEFS_ENV={self.env_dir} mount.objectivefs destroy {filesystem_name}"
        self.run_destroy_command(command)

        self.output_pane.append(f"Destruction initiated for filesystem '{filesystem_name}'.\n")
        self.output_pane.append("Please follow prompts in the terminal window.\n Be aware that the window could be behind this one!")

        progress_dialog.setValue(1)

    def run_command(self, command):
        """Run a shell command, capturing and displaying output."""
        try:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            return output.decode('utf-8')
        except subprocess.CalledProcessError as e:
            self.output_pane.append(f"Error: {e.output.decode('utf-8')}\n")
            return None
        except subprocess.TimeoutExpired:
            self.output_pane.append("Command timed out.\n")
            return None

    def run_destroy_command(self, command):
        """Run a command in an external terminal for user input, capturing and displaying output."""
        if platform.system() == "Linux":
            # Example for Linux systems, adjust to bring focus to the terminal if possible
            full_command = f"gnome-terminal -- bash -c \"{command}; echo 'Press Enter to close...'; read -r\""
        elif platform.system() == "Darwin":  # macOS
            # Run command in macOS terminal
            full_command = f"""osascript -e 'tell app "Terminal" to do script "{command}; echo \\"Press Enter to close...\\"; read -r"'"""
        else:
            self.output_pane.append("Unsupported platform for automatic terminal input.\n")
            return None

        try:
            subprocess.Popen(full_command, shell=True)
            self.output_pane.append(f"Running command in external terminal: {command}\n")
        except Exception as e:
            self.output_pane.append(f"Failed to run command in external terminal: {str(e)}\n")
