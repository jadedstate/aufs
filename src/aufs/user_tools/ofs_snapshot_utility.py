import os
import sys
import glob
import subprocess
import platform
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QProgressDialog,
                               QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QCheckBox)

class SnapshotUtility(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ObjectiveFS Snapshot Utility")
        self.setGeometry(100, 100, 1200, 600)
        self.required_files = ["OBJECTIVEFS_LICENSE", "OBJECTIVEFS_PASSPHRASE"]
        self.snapshot_cache = {}  # In-memory storage for loaded snapshots
        self.mounted_snapshots = []  # List to store mounted snapshots
        self.admin_mode = False
        self.admin_env_dir = None

                

        # Detect OS and set the mount directory accordingly
        self.os_mount = "Volumes" if platform.system() == "Darwin" else "mnt"

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Env Directory Selection
        env_layout = QHBoxLayout()
        env_label = QLabel("Env Directory:")
        self.env_input = QLineEdit()
        self.env_browse_button = QPushButton("Browse")
        self.env_browse_button.clicked.connect(self.browse_env_directory)
        self.env_load_button = QPushButton("Load")
        self.env_load_button.clicked.connect(self.load_env_directory)
        env_layout.addWidget(env_label)
        env_layout.addWidget(self.env_input)
        env_layout.addWidget(self.env_browse_button)
        env_layout.addWidget(self.env_load_button)
        main_layout.addLayout(env_layout)

        # S3 Buckets List
        buckets_layout = QVBoxLayout()
        buckets_layout.addWidget(QLabel("S3 Buckets - DON'T FORGET TO ENTER sudo PASSWORD IN CONSOLE!"))
        self.s3_bucket_list = QListWidget()
        self.s3_bucket_list.setSelectionMode(QListWidget.SingleSelection)
        self.s3_bucket_list.itemSelectionChanged.connect(self.check_bucket_snapshots)
        self.s3_bucket_list.setFixedHeight(200)
        buckets_layout.addWidget(self.s3_bucket_list)
        self.load_refresh_button = QPushButton("Load Snapshots")
        self.load_refresh_button.clicked.connect(self.toggle_load_or_refresh)
        self.load_refresh_button.setEnabled(False)
        buckets_layout.addWidget(self.load_refresh_button)
        main_layout.addLayout(buckets_layout)

        # Snapshots Display with Dual Lists and Multi-Select Toggle
        snapshot_display_layout = QHBoxLayout()
        
        # Available Snapshots
        available_snapshots_layout = QVBoxLayout()
        available_snapshots_layout.addWidget(QLabel("Available Snapshots"))
        self.available_snapshot_list = QListWidget()
        self.available_snapshot_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.available_snapshot_list.setFixedHeight(400)
        available_snapshots_layout.addWidget(self.available_snapshot_list)
        snapshot_display_layout.addLayout(available_snapshots_layout)

        # Mounted Snapshots
        mounted_snapshots_layout = QVBoxLayout()
        mounted_snapshots_layout.addWidget(QLabel("Mounted Snapshots"))
        self.mounted_snapshot_list = QListWidget()
        self.mounted_snapshot_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.mounted_snapshot_list.setFixedHeight(400)
        mounted_snapshots_layout.addWidget(self.mounted_snapshot_list)
        snapshot_display_layout.addLayout(mounted_snapshots_layout)

        main_layout.addLayout(snapshot_display_layout)

        # Multi-Select Toggle
        self.multi_select_toggle = QCheckBox("Enable Multi-Select")
        self.multi_select_toggle.stateChanged.connect(self.toggle_multi_select)
        main_layout.addWidget(self.multi_select_toggle)

        # Admin Mode Button
        self.admin_button = QPushButton("Enable Admin Mode")
        self.admin_button.clicked.connect(self.enable_admin_mode)
        main_layout.addWidget(self.admin_button)

        # Mount, Unmount, and Destroy Buttons
        buttons_layout = QHBoxLayout()

        self.mount_button = QPushButton("Mount Selected Snapshots")
        self.mount_button.clicked.connect(self.mount_snapshots)
        self.mount_button.setEnabled(False)
        buttons_layout.addWidget(self.mount_button)

        self.unmount_button = QPushButton("Unmount Selected Snapshots")
        self.unmount_button.clicked.connect(self.unmount_snapshots)
        buttons_layout.addWidget(self.unmount_button)

        self.destroy_button = QPushButton("Destroy Selected Snapshots")
        self.destroy_button.clicked.connect(self.destroy_snapshots)
        self.destroy_button.setEnabled(False)
        buttons_layout.addWidget(self.destroy_button)

        main_layout.addLayout(buttons_layout)

        # Process Output Pane
        self.output_pane = QTextEdit()
        self.output_pane.setReadOnly(True)
        main_layout.addWidget(QLabel("Process Output:"))
        main_layout.addWidget(self.output_pane)

        self.setup_ui()

    def setup_ui(self):
        """Initialize widgets and UI components."""
        self.available_snapshot_list.setSelectionMode(QListWidget.SingleSelection)
        self.mounted_snapshot_list.setSelectionMode(QListWidget.SingleSelection)

        # Connect the checkbox to toggle selection mode dynamically
        self.multi_select_toggle.stateChanged.connect(self.handle_multi_select_toggle)

    def handle_multi_select_toggle(self, state):
        """Handle the toggle between single-select and multi-select modes and clear selection."""
        
        # Log the current checkbox state just once, clearly
        self.output_pane.append(f"Checkbox state: {state}\n")
        
        # Clear the selection from both lists
        self.available_snapshot_list.clearSelection()
        self.mounted_snapshot_list.clearSelection()
        
        if state == 2:  # Multi-Select mode
            self.available_snapshot_list.setSelectionMode(QListWidget.MultiSelection)
            self.mounted_snapshot_list.setSelectionMode(QListWidget.MultiSelection)
            self.output_pane.append("Multi-Select mode enabled.\n")
            print("Multi-Select mode enabled")
            
        elif state == 0:  # Single-Select mode
            self.available_snapshot_list.setSelectionMode(QListWidget.SingleSelection)
            self.mounted_snapshot_list.setSelectionMode(QListWidget.SingleSelection)
            self.output_pane.append("Single-Select mode enabled.\n")
            print("Single-Select mode enabled")

    def enable_admin_mode(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Admin Env Directory")
        if directory:
            self.load_admin_mode(directory)
            self.output_pane.append(f"Admin mode enabled with directory: {directory}\n")
        else:
            QMessageBox.warning(self, "Admin Mode", "No directory selected for admin mode.")

    def validate_env_directory(self, directory):
        error_message = "Unknown error, nothing mounted."
        missing_files = [file for file in self.required_files if not os.path.exists(os.path.join(directory, file))]
        if missing_files:
            error_message = f"Missing required files: {', '.join(missing_files)}. "

        key_files = glob.glob(os.path.join(directory, '*KEY*')) + glob.glob(os.path.join(directory, '*CREDENTIAL*'))
        if not key_files:
            error_message += "Missing key files (e.g., ACCESS_KEY, SECRET_KEY, etc.). "

        if not os.access(directory, os.R_OK):
            error_message += "Directory is not readable. "
        
        if "Unknown error" in error_message:
            self.output_pane.append(f"Env directory validated: {directory}\n")
            return True

        self.output_pane.append(error_message + "\n")
        return False

    def browse_env_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Env Directory")
        if directory:
            self.env_input.setText(directory)
            self.load_env_directory()

    def load_env_directory(self):
        directory = self.env_input.text()
        if directory and os.path.isdir(directory):
            if self.validate_env_directory(directory):
                self.populate_s3_buckets()
                self.check_existing_mounts()  # Check for already mounted snapshots
            else:
                QMessageBox.warning(self, "Invalid Env Directory", "The selected directory does not contain the required ObjectiveFS files.")
                self.s3_bucket_list.setEnabled(False)
        else:
            QMessageBox.warning(self, "Invalid Path", "The provided path is not a valid directory.")

    def load_admin_mode(self, admin_env_dir):
        """Switches to admin mode for using admin commands like destroy."""
        self.admin_env_dir = admin_env_dir
        self.admin_mode = True
        self.output_pane.append("Admin mode activated.\n")

    def check_existing_mounts(self):
        """Check for already mounted snapshots with the prefix 'ss_'."""
        self.mounted_snapshot_list.clear()
        try:
            output = subprocess.check_output("mount", shell=True).decode('utf-8')
            for line in output.splitlines():
                if f"/{self.os_mount}/ss_" in line:
                    # Extract the snapshot name from the mount point
                    mount_point = line.split()[2]
                    snapshot = mount_point.split('/')[-1].replace("ss_", "")  # Get the snapshot name
                    display_text = snapshot.replace('_', ' ')  # Format the snapshot name for display
                    self.mounted_snapshots.append({"name": snapshot, "display": display_text})
                    self.mounted_snapshot_list.addItem(QListWidgetItem(display_text))
            self.output_pane.append("Existing mounted snapshots loaded.\n")
        except subprocess.CalledProcessError as e:
            self.output_pane.append(f"Error checking mounts: {e.output.decode('utf-8')}\n")

    def check_bucket_snapshots(self):
        selected_bucket_items = self.s3_bucket_list.selectedItems()
        if not selected_bucket_items:
            self.load_refresh_button.setEnabled(False)
            return

        selected_bucket = selected_bucket_items[0].text().split()[0]  # Use only the bucket name

        if selected_bucket in self.snapshot_cache:
            self.load_refresh_button.setText("Refresh Snapshots")
            self.load_refresh_button.setEnabled(True)
            self.display_snapshots(selected_bucket)
        else:
            self.load_refresh_button.setText("Load Snapshots")
            self.load_refresh_button.setEnabled(True)

    def toggle_load_or_refresh(self):
        selected_bucket_items = self.s3_bucket_list.selectedItems()
        if not selected_bucket_items:
            return

        selected_bucket = selected_bucket_items[0].text().split()[0]  # Use only the bucket name

        if self.load_refresh_button.text() == "Load Snapshots":
            self.load_snapshots(selected_bucket)
        elif self.load_refresh_button.text() == "Refresh Snapshots":
            self.refresh_snapshots(selected_bucket)

    def refresh_snapshots(self, bucket):
        self.load_snapshots(bucket)  # Reuse load_snapshots method for simplicity

    def display_snapshots(self, bucket):
        self.available_snapshot_list.clear()
        self.mounted_snapshot_list.clear()

        snapshots = self.snapshot_cache[bucket]
        snapshots.sort(key=lambda snap: snap["name"], reverse=True)  # Sort in reverse chronological order

        for snapshot in snapshots:
            if snapshot["name"] in [snap["name"] for snap in self.mounted_snapshots]:
                item = QListWidgetItem(snapshot["display"])
                self.mounted_snapshot_list.addItem(item)
            else:
                item = QListWidgetItem(snapshot["display"])
                self.available_snapshot_list.addItem(item)

        self.output_pane.append(f"Snapshots displayed for {bucket}.\n")
        self.mount_button.setEnabled(True)
        self.destroy_button.setEnabled(True)  # Enable the destroy button when snapshots are displayed

    def mount_snapshots(self):
        selected_snapshots = [item.text() for item in self.available_snapshot_list.selectedItems()]  # Use only the display name

        for display_name in selected_snapshots:
            # Find the actual snapshot name from the display name
            snapshot = next(snap["name"] for snap in self.snapshot_cache[self.s3_bucket_list.currentItem().text().split()[0]]
                            if snap["display"] == display_name)

            # Prepend 'ss_' to the mount name for easy identification
            mount_point = f"/{self.os_mount}/ss_{self.sanitize_mount_name(snapshot)}"

            if self.is_mounted(mount_point):
                self.output_pane.append(f"Snapshot {snapshot} is already mounted at {mount_point}. Skipping.\n")
                continue

            command = f"mount.objectivefs -o mt,bulkdata,noatime,nodiratime,mkdir {snapshot} {mount_point}"
            self.run_command(command)

            # Move snapshot from available to mounted list
            self.mounted_snapshots.append({"name": snapshot, "display": display_name})
            item = QListWidgetItem(display_name)
            self.mounted_snapshot_list.addItem(item)

            # Remove snapshot from available list
            items_to_remove = self.available_snapshot_list.findItems(display_name, Qt.MatchExactly)
            for item in items_to_remove:
                self.available_snapshot_list.takeItem(self.available_snapshot_list.row(item))

    def unmount_snapshots(self):
        selected_snapshots = [item.text() for item in self.mounted_snapshot_list.selectedItems()]  # Use only the display name

        for display_name in selected_snapshots:
            # Find the actual snapshot name from the display name
            snapshot = next(snap["name"] for snap in self.mounted_snapshots if snap["display"] == display_name)

            # Prepend 'ss_' to the mount name
            mount_point = f"/{self.os_mount}/ss_{self.sanitize_mount_name(snapshot)}"
            command = f"umount {mount_point}"
            self.run_command(command)

            # Move snapshot from mounted to available list
            self.mounted_snapshots = [snap for snap in self.mounted_snapshots if snap["name"] != snapshot]
            item = QListWidgetItem(display_name)
            self.available_snapshot_list.addItem(item)

            # Remove snapshot from mounted list
            items_to_remove = self.mounted_snapshot_list.findItems(display_name, Qt.MatchExactly)
            for item in items_to_remove:
                self.mounted_snapshot_list.takeItem(self.mounted_snapshot_list.row(item))

    def toggle_multi_select(self, state):
        """Toggle between single-select and multi-select modes."""
        if state == Qt.Checked:
            self.available_snapshot_list.setSelectionMode(QListWidget.MultiSelection)
            self.mounted_snapshot_list.setSelectionMode(QListWidget.MultiSelection)
            self.output_pane.append("Multi-Select mode enabled.\n")
        else:
            self.available_snapshot_list.setSelectionMode(QListWidget.SingleSelection)
            self.mounted_snapshot_list.setSelectionMode(QListWidget.SingleSelection)
            self.output_pane.append("Single-Select mode enabled.\n")

    def destroy_snapshots(self):
        """Destroy selected snapshots (handles both single and multiple) with progress feedback."""
        selected_snapshots = [item.text() for item in self.available_snapshot_list.selectedItems()]  # Get selected snapshots

        if not selected_snapshots:
            self.output_pane.append("No snapshots selected for destruction.\n")
            return

        # Confirmation prompt
        num_snapshots = len(selected_snapshots)
        confirmation = QMessageBox.question(
            self,
            "Confirm Destruction",
            f"Are you sure you want to destroy {num_snapshots} snapshot(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmation != QMessageBox.Yes:
            self.output_pane.append("Snapshot destruction canceled by user.\n")
            return

        bucket_name = self.s3_bucket_list.currentItem().text().split()[0]  # Get the current bucket

        # Initialize progress dialog
        progress_dialog = QProgressDialog("Destroying snapshots...", "Cancel", 0, len(selected_snapshots), self)
        progress_dialog.setWindowTitle("Snapshot Destruction Progress")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.show()

        failed_destructions = []

        for idx, display_name in enumerate(selected_snapshots):
            if progress_dialog.wasCanceled():
                self.output_pane.append("Snapshot destruction canceled by user.\n")
                break

            # Update the progress dialog
            progress_dialog.setValue(idx)
            progress_dialog.setLabelText(f"Destroying snapshot {display_name}...")
            QApplication.processEvents()  # Allow the UI to update

            # Find the actual snapshot name from the display name
            snapshot = next((snap["name"] for snap in self.snapshot_cache[bucket_name] 
                            if snap["display"] == display_name), None)

            if not snapshot:
                self.output_pane.append(f"Snapshot {display_name} not found in cache.\n")
                continue

            # Prepare the destroy command using 'yes' to continuously confirm destruction
            command = f"mount.objectivefs destroy {snapshot}"

            # Run the destroy command using the run_command method
            output = self.run_command(command, admin=True)

            if output:
                self.output_pane.append(f"Snapshot {snapshot} destroyed successfully.\n")
            else:
                self.output_pane.append(f"Failed to destroy snapshot {snapshot}.\n")
                failed_destructions.append(snapshot)  # Keep track of any failed destructions

        # Ensure the progress bar reaches 100%
        progress_dialog.setValue(len(selected_snapshots))

        # Reload snapshots from the source after all destruction attempts (reflect the true state)
        self.load_snapshots(bucket_name)

        if failed_destructions:
            self.output_pane.append(f"Failed to destroy: {', '.join(failed_destructions)}.\n")


    def is_mounted(self, mount_point):
        """Check if the given mount point is already mounted."""
        try:
            output = subprocess.check_output("mount", shell=True).decode('utf-8')
            return mount_point in output
        except subprocess.CalledProcessError as e:
            self.output_pane.append(f"Error checking mounts: {e.output.decode('utf-8')}\n")
        return False

    def sanitize_mount_name(self, snapshot_name):
        """Sanitize snapshot name for use as a mount point by replacing invalid characters."""
        sanitized_name = snapshot_name.replace('://', '_').replace('@', '_').replace(':', '_')
        return sanitized_name

    def populate_s3_buckets(self):
        self.s3_bucket_list.clear()
        command = "mount.objectivefs list -a"
        output = self.run_command(command)
        
        if output:
            data_lines = self.parse_output(output)
            buckets = self.extract_buckets(data_lines)
            
            if not buckets:
                self.s3_bucket_list.addItem("No buckets found.")
                self.mount_button.setEnabled(False)
                return

            for bucket in buckets:
                item = QListWidgetItem(bucket)  # Display full bucket info
                self.s3_bucket_list.addItem(item)
            self.s3_bucket_list.setEnabled(True)
            self.load_refresh_button.setEnabled(True)
        else:
            self.s3_bucket_list.addItem("Error fetching buckets.")
            self.mount_button.setEnabled(False)

    def load_snapshots(self, bucket):
        """Load snapshots for the selected bucket."""
        command = f"mount.objectivefs list -s {bucket}"
        output = self.run_command(command)

        if output:
            data_lines = self.parse_output(output)
            snapshots = self.extract_snapshots(data_lines)
            self.snapshot_cache[bucket] = snapshots
            self.display_snapshots(bucket)
        else:
            self.output_pane.append(f"Failed to load snapshots for {bucket}\n")

    def extract_buckets(self, data_lines):
        """Extract bucket details from the parsed data lines."""
        buckets = []
        for line in data_lines:
            bucket = line.split()[0]  # Extract only the bucket name for variables
            buckets.append(line)  # Store the full line for display
        return buckets

    def extract_snapshots(self, data_lines):
        """Extract snapshot details from the parsed data lines."""
        snapshots = []
        for line in data_lines:
            snapshot_name = line.split()[0]  # Extract only the snapshot name for variables
            display_text = '    '.join(line.split('T'))  # Prepare the display text
            snapshots.append({"name": snapshot_name, "display": display_text})  # Store both name and display text
        return snapshots

    def parse_output(self, output):
        """Parse the output based on headings and extract data rows."""
        data_lines = []
        headings_found = False

        for line in output.splitlines():
            if "NAME" in line and "KIND" in line and "SNAP" in line:
                headings_found = True
                continue  # Skip the headings line itself

            if headings_found:
                if line.strip():
                    data_lines.append(line.strip())
                else:
                    break  # Stop if we encounter an empty line after data starts

        return data_lines

    def run_command(self, command, admin=False):
        """Run a command, using sudo if admin is set."""
        env_dir = self.admin_env_dir if admin else self.env_input.text()  # Use admin env if specified
        if admin:
            full_command = f"yes | sudo OBJECTIVEFS_ENV={env_dir} {command}"  # Prepend the environment variable to the command
        else:
            full_command = f"sudo OBJECTIVEFS_ENV={env_dir} {command}"  # Prepend the environment variable to the command

        try:
            output = subprocess.check_output(full_command, shell=True, stderr=subprocess.STDOUT)
            self.output_pane.append(f"Command: {full_command}\nOutput:\n{output.decode('utf-8')}\n")
            return output.decode('utf-8')
        except subprocess.CalledProcessError as e:
            self.output_pane.append(f"Command: {full_command}\nError: {e.output.decode('utf-8')}\n")
            return None
        except subprocess.TimeoutExpired:
            self.output_pane.append(f"Command timed out: {full_command}\n")
            return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SnapshotUtility()
    window.show()
    sys.exit(app.exec())
