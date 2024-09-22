import sys
import os
import json
import time
import subprocess
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QListWidget, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton,
                               QCheckBox, QVBoxLayout, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from pathlib import Path
import pyarrow.parquet as pq
import platform
import textwrap

class AUFS(QMainWindow):
    def __init__(self):
        super().__init__()

        # Ensure ~/.aufs/parquet directory exists
        self.setup_aufs_directories()

        # Setup the window
        self.setWindowTitle("AUFS Provisioner Tool")
        self.setGeometry(300, 300, 600, 400)

        # Main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add buttons
        self.package_button = QPushButton("Create Package", self)
        self.aufs_info_button = QPushButton("auFS Info", self)
        self.template_button = QPushButton("Provision AUFS", self)  # Provision button
        layout.addWidget(self.package_button)
        layout.addWidget(self.aufs_info_button)
        layout.addWidget(self.template_button)

        self.package_button.clicked.connect(self.create_double_clickable_package)
        self.aufs_info_button.clicked.connect(self.show_aufs_info)
        self.template_button.clicked.connect(self.provision_aufs)

        # Add the list widget for schema files
        self.schema_list = QListWidget(self)
        layout.addWidget(self.schema_list, stretch=1)

        # Add refresh button for the schema list
        self.refresh_button = QPushButton("Refresh List", self)
        layout.addWidget(self.refresh_button)

        self.refresh_button.clicked.connect(self.refresh_schema_list)

        # Populate schema list on startup
        self.refresh_schema_list()

        # With a single checkbox for user credentials:
        self.checkbox_credentials = QCheckBox("User Credentials (Username & Password)", self)
        self.checkbox_root_dir = QCheckBox("Root Dir (Mount Point)", self)
        self.checkbox_spare = QCheckBox("Spare", self)

        # Set checkboxes to be checked by default
        self.checkbox_credentials.setChecked(True)
        self.checkbox_root_dir.setChecked(True)
        self.checkbox_spare.setChecked(False)

        # Add checkboxes to the layout
        layout.addWidget(self.checkbox_credentials)
        layout.addWidget(self.checkbox_root_dir)
        layout.addWidget(self.checkbox_spare)

    def show_aufs_info(self):
        """
        Show the AUFS Information dialog, including schema, metadata, and data from the Parquet file.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            parquet_file = self.get_embedded_parquet_path(selected_item.text())  # Path to embedded Parquet file

            try:
                # Read the Parquet file
                parquet_table = pq.read_table(parquet_file)

                # Extract schema, metadata, and data
                schema = parquet_table.schema
                metadata = schema.metadata
                data = parquet_table.to_pandas()

                # Show the info dialog
                info_dialog = AUFSInfoDialog(schema=schema, metadata=metadata, data=data, parent=self)
                info_dialog.exec_()

            except Exception as e:
                print(f"Error reading Parquet file: {e}")

    def setup_aufs_directories(self):
        """
        Ensures that the ~/.aufs/parquet directory structure is in place.
        """
        home_dir = str(Path.home())
        self.parquet_dir = os.path.join(home_dir, '.aufs', 'parquet')
        os.makedirs(self.parquet_dir, exist_ok=True)

    def refresh_schema_list(self):
        """
        Refreshes the list of files in the ~/.aufs/parquet directory, recursively.
        Filters out invisible files (files that start with a dot).
        """
        self.schema_list.clear()

        # Recursively gather files in the parquet directory, filtering out hidden files
        file_list = []
        for root, dirs, files in os.walk(self.parquet_dir):
            for file in files:
                if not file.startswith('.'):  # Skip hidden files
                    full_path = os.path.join(root, file)
                    # Strip the base path so we don't show the "parquet" directory itself
                    relative_path = os.path.relpath(full_path, self.parquet_dir)
                    file_list.append(relative_path)

        # Sort the files
        file_list.sort()

        # Add files to the schema list
        for file in file_list:
            self.schema_list.addItem(file)

    def provision_aufs(self):
        """
        Provision AUFS by detecting the current platform and executing the corresponding script from the first column of the Parquet file.
        The checkboxes control whether the user is prompted for username, password, or root directory.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            parquet_file = self.get_embedded_parquet_path(selected_item.text())  # Path to embedded Parquet file

            try:
                # Step 1: Read the Parquet file
                parquet_table = pq.read_table(parquet_file)
                metadata = parquet_table.schema.metadata

                if metadata:
                    # Step 2: Get the platform key
                    platform_key = self.get_platform_key()

                    # Step 3: Extract the platform scripts metadata
                    platform_scripts = json.loads(metadata.get(b'platform_scripts', '{}').decode('utf-8'))

                    # Step 4: Find the row index for the current platform
                    if platform_key in platform_scripts:
                        row_index = int(platform_scripts[platform_key])  # Convert the string index to an integer

                        # Step 5: Extract the script from the first column
                        script = parquet_table.to_pandas().iloc[row_index, 0]  # Always get the first column

                        # **HANDLE CHECKBOX LOGIC**
                        # If a checkbox is unchecked, skip prompts and replacements for username, password, or mount point.

                        # 1. Handle Credentials (User & Password) checkbox
                        if self.checkbox_credentials.isChecked():
                            # Prompt for username and replace "UNAME" in the script if checked
                            username = self.prompt_for_username()
                            password = self.prompt_for_password()
                            if username:
                                script = script.replace("UNAME", username)
                            if password:
                                script = script.replace("PSSWD", password)
                        else:
                            # Skip username and password prompt and remove UNAME and PSSWD placeholders if unchecked
                            script = script.replace("UNAME", "").replace("PSSWD", "")

                        # 2. Handle Root Dir (Mount Point) checkbox
                        if self.checkbox_root_dir.isChecked():
                            # Prompt for mount point and replace "MNTPOINT" in the script if checked
                            mount_point = self.prompt_for_mount_point()
                            if mount_point:
                                script = script.replace("MNTPOINT", mount_point)
                        else:
                            # Skip mount point prompt and remove MNTPOINT placeholder if unchecked
                            script = script.replace("MNTPOINT", "")

                        # Step 6: Execute the script
                        self.execute_embedded_script(script)

                    else:
                        print(f"No script found for platform: {platform_key}")
                else:
                    print("No metadata found in the Parquet file.")
            except Exception as e:
                print(f"Error reading Parquet file: {e}")

    def prompt_for_username(self):
        """
        Prompts the user for their username.
        """
        username, ok = QInputDialog.getText(self, "Username", "Enter your username:")
        if ok and username:
            return username
        return None

    def prompt_for_password(self):
        """
        Prompts the user for their password.
        """
        password, ok = QInputDialog.getText(self, "Password", "Enter your password:", QLineEdit.Password)
        if ok and password:
            return password
        return None

    def prompt_for_mount_point(self):
        """
        Prompts the user for the root directory (mount point) to use.
        - On Windows, it asks for a drive letter.
        - On macOS/Linux, it asks for a directory.
        """
        system_platform = platform.system().lower()

        if system_platform == 'windows':
            # Ask for a drive letter on Windows
            mount_point, ok = QInputDialog.getText(self, "Drive Letter", "Enter a drive letter (e.g., Z):", QLineEdit.Normal, "Z")
            if ok and mount_point:
                return mount_point.upper()  # Normalize to uppercase drive letter
        else:
            # Ask for a directory on macOS/Linux
            mount_point = QFileDialog.getExistingDirectory(self, "Select Mount Point")
            if mount_point:
                return mount_point
        return None

    def get_shell_command(self):
        """
        Return the appropriate shell command and flag for the current platform.
        """
        system_platform = platform.system().lower()

        if system_platform == "windows":
            # Use PowerShell for running PowerShell script
            shell = "powershell"
            flag = "-Command"
        elif system_platform == "darwin" or system_platform == "linux":
            shell = "bash"  # Use bash on macOS and Linux
            flag = "-c"
        else:
            raise Exception(f"Unsupported platform: {system_platform}")

        return shell, flag

    def execute_embedded_script(self, script):
        """
        Execute the platform-specific script extracted from the Parquet file.
        Run the script quietly and only display success or failure.
        """
        shell, flag = self.get_shell_command()

        try:
            if script:
                # **DEBUGGING**: Print the script for review
                print(f"Executing the following script: \n{script}")

                # Execute the script in the correct shell and capture both stdout and stderr
                print(f"Executing script using {shell}:")
                result = subprocess.run([shell, flag, script], check=True, capture_output=True, text=True)

                # Print the output and errors for debugging
                print(f"Stdout: {result.stdout}")
                print(f"Stderr: {result.stderr}")

                # Check if the script ran successfully
                print("Script executed successfully.")
            else:
                print("No script found to execute.")
        except subprocess.CalledProcessError as e:
            # If an error occurs, report the failure
            print(f"Error executing script: {e}")
            print(f"Script execution failed with stderr: {e.stderr}")
            
    def run_provisioning_workflow(self, parquet_path):
        """
        The full workflow of reading the Parquet file, extracting the platform-specific script, and executing it.
        """
        try:
            # Step 1: Detect platform
            platform_key = self.get_platform_key()
            print(f"Detected platform: {platform_key}")

            # Step 2: Read Parquet file
            schema, script = self.read_parquet_for_platform(parquet_path, platform_key)

            if script:
                print(f"Found script for platform '{platform_key}':\n{script}")
                # Step 3: Execute script
                self.execute_script(script)
            else:
                print(f"No script found for platform: {platform_key}")
                QMessageBox.warning(self, "No Script", f"No script found for platform '{platform_key}'.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during provisioning: {str(e)}")

    def get_platform_key(self):
        """
        Detect the current platform and return the corresponding key to use in the Parquet file metadata.
        """
        if platform.system().lower() == "windows":
            return "win_script"
        elif platform.system().lower() == "darwin":
            return "darwin_script"
        elif platform.system().lower() == "linux":
            return "linux_script"
        else:
            raise Exception("Unsupported platform!")

    def read_parquet_for_platform(self, parquet_path, platform_key):
        """
        Reads the Parquet file and extracts schema and platform-specific script from the metadata.
        :param parquet_path: Path to the Parquet file.
        :param platform_key: Key to identify which script to extract based on the platform.
        :return: Tuple of schema fields and script.
        """
        # Open parquet file using pyarrow
        parquet_file = pq.ParquetFile(parquet_path)
        metadata = parquet_file.metadata
        print('Parquet md: ')
        print(metadata)

        # Extract key-value metadata and look for platform-specific script
        schema_fields = metadata.schema.names
        script = None

        if metadata is not None:
            kv_metadata = metadata.metadata
            if kv_metadata is not None and platform_key.encode('utf-8') in kv_metadata:
                script = kv_metadata[platform_key.encode('utf-8')].decode('utf-8')

        return schema_fields, script

    def provision_schema(self):
        """
        Provision AUFS by detecting the current platform, creating directories, and executing the corresponding script.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            parquet_file = os.path.join(self.parquet_dir, selected_item.text())  # Full path to the Parquet file

            try:
                # Step 1: Read the Parquet file
                parquet_table = pq.read_table(parquet_file)
                self.metadata = parquet_table.schema.metadata  # Store metadata for directory creation

                if self.metadata:
                    # Step 2: Create directory tree
                    self.create_directory_tree()

                    # Step 3: Get the platform key
                    platform_key = self.get_platform_key()

                    # Step 4: Extract the platform scripts metadata
                    platform_scripts = json.loads(self.metadata.get(b'platform_scripts', '{}').decode('utf-8'))

                    # Step 5: Find the row index for the current platform
                    if platform_key in platform_scripts:
                        row_index = int(platform_scripts[platform_key])  # Convert the string index to an integer

                        # Step 6: Extract the script from the first column, regardless of its name
                        script = parquet_table.to_pandas().iloc[row_index, 0]  # Always get the first column, regardless of the name

                        # Step 7: Execute the script
                        subprocess.run(script, shell=True)
                    else:
                        print(f"No script found for platform: {platform_key}")
                else:
                    print("No metadata found in the Parquet file.")
            except Exception as e:
                print(f"Error reading Parquet file: {e}")

    def create_directory_tree(self):
        # Step 1: Extract the directory tree from the metadata
        directory_tree = json.loads(self.metadata[b'directory_tree'].decode('utf-8'))
        uuid_dirname_mapping = json.loads(self.metadata[b'uuid_dirname_mapping'].decode('utf-8'))

        # Step 2: Traverse the directory tree
        for parent_uuid, children in directory_tree.items():
            # Map parent UUID to directory name
            parent_dir = uuid_dirname_mapping.get(parent_uuid)
            if not parent_dir:
                continue

            # Create the parent directory
            parent_dir_path = os.path.join(self.parquet_dir, parent_dir)
            os.makedirs(parent_dir_path, exist_ok=True)

            # Create child directories
            for child in children:
                child_name = uuid_dirname_mapping.get(child["id"])
                if child_name:
                    child_dir_path = os.path.join(parent_dir_path, child_name)
                    os.makedirs(child_dir_path, exist_ok=True)

    def generate_provisioner_script(self, parquet_file):
        """
        Generates a Python script with the provisioning logic for the selected Parquet file.
        :param parquet_file: The path to the selected Parquet file.
        :return: The path to the generated Python script.
        """
        # Get the base name of the parquet file (without extension) and current UTC timestamp
        parquet_name = os.path.splitext(os.path.basename(parquet_file))[0]
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        script_name = f"{parquet_name}_{timestamp}.py"

        # Define the target directory to store the script
        target_dir = os.path.join(str(Path.home()), f".aufs/provisioning/pyinstaller/{parquet_name}")
        os.makedirs(target_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # Path for the new Python script
        script_path = os.path.join(target_dir, script_name)

        # Define the provisioning logic script, replacing {parquet_file} with the actual path
        provisioner_script = f"""
        import sys
        import os
        import json
        import subprocess
        import platform
        import pyarrow.parquet as pq
        import tkinter as tk
        from tkinter import messagebox, simpledialog, filedialog

        class ParquetProvisioner:
            def __init__(self, parquet_path):
                self.parquet_path = parquet_path
                self.username = None
                self.password = None
                self.mount_point = None
                self.is_ofs = False  # Added to track if this is an OFS provisioner

            def run(self):
                parquet_table = pq.read_table(self.parquet_path)
                metadata = parquet_table.schema.metadata

                if metadata:
                    # Detect if this is an OFS provisioner
                    self.is_ofs = self.detect_ofs_provisioner(metadata)

                    if self.is_ofs:
                        self.get_user_creds_ofs_docker_01()  # Use the specific OFS method
                    else:
                        self.get_user_credentials()  # Get username, password, and mount point

                    dir_tree_preview = self.get_directory_tree_preview(metadata)
                    proceed = self.show_preview_and_confirm(dir_tree_preview)

                    if proceed:
                        self.provision_schema(metadata)
                        platform_key = self.get_platform_key()
                        self.execute_platform_script(metadata, platform_key)

            def detect_ofs_provisioner(self, metadata):
                # Detect if this is an OFS provisioner by examining the metadata
                try:
                    first_chunk = pq.read_table(self.parquet_path).to_pandas().iloc[0, 0].lower()
                    if 'objectivefs' in first_chunk:
                        return True
                    return False
                except Exception as e:
                    print(f"Error detecting OFS provisioner: {{e}}")
                    return False

            def get_user_credentials(self):
                # Initialize Tkinter root window
                root = tk.Tk()
                root.withdraw()  # Hide the root window

                # Prompt for username and password
                self.username = simpledialog.askstring("Username", "Enter your username:")
                self.password = simpledialog.askstring("Password", "Enter your password:", show='*')

                # Platform-specific handling
                if platform.system().lower() == 'windows':
                    # **Prompt for drive letter on Windows**
                    self.mount_point = simpledialog.askstring("Drive Letter", "Enter a drive letter (e.g., Z):", initialvalue="Z")

                    if not self.mount_point:
                        messagebox.showerror("Error", "You must provide a drive letter.")
                        sys.exit(1)  # Exit if no drive letter is provided

                    # Normalize the input to uppercase and ensure it's valid
                    self.mount_point = self.mount_point.strip().upper()

                    # Validate that the input is a single alphabetic character (e.g., "Z")
                    if len(self.mount_point) != 1 or not self.mount_point.isalpha():
                        messagebox.showerror("Error", "Invalid drive letter. Please enter a valid drive letter (e.g., Z).")
                        sys.exit(1)
                else:
                    # **Prompt for mount point using a directory browser for macOS/Linux**
                    self.mount_point = filedialog.askdirectory(title="Select Mount Point")

                    if not self.mount_point:
                        messagebox.showerror("Error", "You must select a valid mount point.")
                        sys.exit(1)  # Exit if no directory is selected

            def get_user_creds_ofs_docker_01(self):
                
                # This method is specifically used for OFS provisioning.
                # It sets the mount point and ensures the directory is valid and empty.
                
                # Prompt for mount point (an empty directory) using a directory browser
                self.mount_point = filedialog.askdirectory(title="Select an empty directory as the mount point")

                # Ensure the mount point is empty and valid
                if not self.mount_point or not os.path.exists(self.mount_point):
                    messagebox.showerror("Error", "Invalid directory. Please select an empty directory.")
                    sys.exit(1)

                if os.listdir(self.mount_point):
                    messagebox.showerror("Error", "The selected directory is not empty. Please choose another directory.")
                    sys.exit(1)

                # Set empty values for username and password to avoid replacement errors later
                self.username = ""  # No need for a username in OFS context, set it to an empty string
                self.password = ""  # No need for a password in OFS context, set it to an empty string

                print(f"Selected mount point: {{self.mount_point}}")

            def get_directory_tree_preview(self, metadata):
                directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
                uuid_dirname_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
                tree_preview = ""
                for parent_uuid, children in directory_tree.items():
                    parent_dir = uuid_dirname_mapping.get(parent_uuid, "Data_root")
                    tree_preview += f"Parent: {{parent_dir}}\\n"
                    for child in children:
                        child_dir = uuid_dirname_mapping.get(child['id'], "Data_root")
                        tree_preview += f"  └─ {{child_dir}}\\n"
                return tree_preview

            def show_preview_and_confirm(self, tree_preview):
                # Initialize Tkinter root window
                root = tk.Tk()
                root.withdraw()  # Hide the root window

                # Show the directory tree preview and ask for confirmation
                message = f"Preview of directory tree:\\n\\n{{tree_preview}}\\nDo you want to proceed with provisioning?"
                return messagebox.askokcancel("Directory Tree Preview", message)

            def provision_schema(self, metadata):
                directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
                uuid_dirname_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
                for parent_uuid, children in directory_tree.items():
                    parent_dir = uuid_dirname_mapping.get(parent_uuid)
                    if not parent_dir:
                        continue
                    parent_dir_path = os.path.join(self.mount_point, parent_dir)  # Use selected mount point
                    os.makedirs(parent_dir_path, exist_ok=True)
                    for child in children:
                        child_name = uuid_dirname_mapping.get(child["id"])
                        if child_name:
                            child_dir_path = os.path.join(parent_dir_path, child_name)
                            os.makedirs(child_dir_path, exist_ok=True)

            def execute_platform_script(self, metadata, platform_key):
                platform_scripts = json.loads(metadata.get(b'platform_scripts', '{{}}').decode('utf-8'))
                if platform_key in platform_scripts:
                    row_index = int(platform_scripts[platform_key])
                    script = pq.read_table(self.parquet_path).to_pandas().iloc[row_index, 0]

                    # Inject username, password, and mount point into the script
                    script = script.replace("UNAME", self.username).replace("PSSWD", self.password).replace("MNTPOINT", self.mount_point)

                    # Determine the appropriate shell to use for running the script
                    if platform.system().lower() == 'windows':
                        shell = "powershell.exe"  # Use PowerShell on Windows
                        flag = "-Command"
                    else:
                        shell = "/bin/bash"  # Use bash on macOS/Linux
                        flag = "-c"

                    # Execute the platform-specific script
                    try:
                        print(f"Executing script with {{shell}}:")
                        subprocess.run([shell, flag, script], check=True, shell=False, capture_output=True, text=True)
                    except subprocess.CalledProcessError as e:
                        print(f"Script execution failed: {{e}}")
                        print(f"Stdout: {{e.stdout}}")
                        print(f"Stderr: {{e.stderr}}")

            def get_platform_key(self):
                system_platform = platform.system().lower()
                if system_platform == "windows":
                    return "win_script"
                elif system_platform == "darwin":
                    return "darwin_script"
                elif system_platform == "linux":
                    return "linux_script"
                else:
                    raise Exception("Unsupported platform!")

        if __name__ == "__main__":
            provisioner = ParquetProvisioner(r"{parquet_file}")
            provisioner.run()
        """

        # Write the script content to the file with UTF-8 encoding
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(provisioner_script)

        # Read back with UTF-8 encoding
        with open(script_path, 'r', encoding='utf-8') as script_file:
            script_content = script_file.read()

        # Remove unwanted indentation
        script_content = textwrap.dedent(script_content)

        # Write the fixed script back to the file
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)

        return script_path

    def generate_provisioner_script_clean(self, parquet_file):
        """
        Generates a Python script without any dialogs or variable replacements.
        All information is embedded in the Parquet file.
        """
        # Get the base name of the parquet file (without extension) and current UTC timestamp
        parquet_name = os.path.splitext(os.path.basename(parquet_file))[0]
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        script_name = f"{parquet_name}_{timestamp}.py"

        # Define the target directory to store the script
        target_dir = os.path.join(str(Path.home()), f".aufs/provisioning/pyinstaller/{parquet_name}")
        os.makedirs(target_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # Path for the new Python script
        script_path = os.path.join(target_dir, script_name)

        # Define the provisioning logic script with no dialogs or variable replacements
        provisioner_script = f"""
        import sys
        import os
        import json
        import subprocess
        import platform
        import pyarrow.parquet as pq

        class ParquetProvisioner:
            def __init__(self, parquet_path):
                self.parquet_path = parquet_path

            def run(self):
                parquet_table = pq.read_table(self.parquet_path)
                metadata = parquet_table.schema.metadata

                if metadata:
                    self.provision_schema(metadata)
                    platform_key = self.get_platform_key()
                    self.execute_platform_script(metadata, platform_key)

            def provision_schema(self, metadata):
                directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
                uuid_dirname_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
                for parent_uuid, children in directory_tree.items():
                    parent_dir = uuid_dirname_mapping.get(parent_uuid)
                    if not parent_dir:
                        continue
                    os.makedirs(parent_dir, exist_ok=True)
                    for child in children:
                        child_name = uuid_dirname_mapping.get(child["id"])
                        if child_name:
                            os.makedirs(child_name, exist_ok=True)

            def execute_platform_script(self, metadata, platform_key):
                platform_scripts = json.loads(metadata.get(b'platform_scripts', '{{}}').decode('utf-8'))
                if platform_key in platform_scripts:
                    row_index = int(platform_scripts[platform_key])
                    script = pq.read_table(self.parquet_path).to_pandas().iloc[row_index, 0]

                    if platform.system().lower() == 'windows':
                        shell = 'powershell.exe'
                        flag = '-Command'
                    else:
                        shell = '/bin/bash'
                        flag = '-c'

                    try:
                        result = subprocess.run([shell, flag, script], check=True, capture_output=True, text=True)
                        print(f"Stdout: {{result.stdout}}")
                        print(f"Stderr: {{result.stderr}}")
                    except subprocess.CalledProcessError as e:
                        print(f"Script execution failed: {{e}}")
                        print(f"Stdout: {{e.stdout}}")
                        print(f"Stderr: {{e.stderr}}")

            def get_platform_key(self):
                system_platform = platform.system().lower()
                if system_platform == "windows":
                    return "win_script"
                elif system_platform == "darwin":
                    return "darwin_script"
                elif system_platform == "linux":
                    return "linux_script"
                else:
                    raise Exception("Unsupported platform!")

        if __name__ == "__main__":
            provisioner = ParquetProvisioner(r"{parquet_file}")
            provisioner.run()
        """

        # Write the script content to the file with UTF-8 encoding
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(provisioner_script)

        # Read back with UTF-8 encoding
        with open(script_path, 'r', encoding='utf-8') as script_file:
            script_content = script_file.read()

        # Remove unwanted indentation
        script_content = textwrap.dedent(script_content)

        # Write the fixed script back to the file
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)

        return script_path

    def generate_provisioner_script_root(self, parquet_file):
        """
        Generates a Python script with one dialog asking for a drive letter (Windows) or a directory (macOS/Linux).
        """
        # Get the base name of the parquet file (without extension) and current UTC timestamp
        parquet_name = os.path.splitext(os.path.basename(parquet_file))[0]
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        script_name = f"{parquet_name}_{timestamp}.py"

        # Define the target directory to store the script
        target_dir = os.path.join(str(Path.home()), f".aufs/provisioning/pyinstaller/{parquet_name}")
        os.makedirs(target_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # Path for the new Python script
        script_path = os.path.join(target_dir, script_name)

        # Define the provisioning logic script with one dialog for the root (mount point)
        provisioner_script = f"""
        import sys
        import os
        import json
        import subprocess
        import platform
        import pyarrow.parquet as pq
        import tkinter as tk
        from tkinter import simpledialog, filedialog, messagebox

        class ParquetProvisioner:
            def __init__(self, parquet_path):
                self.parquet_path = parquet_path
                self.mount_point = None

            def run(self):
                parquet_table = pq.read_table(self.parquet_path)
                metadata = parquet_table.schema.metadata

                if metadata:
                    self.get_mount_point()
                    self.provision_schema(metadata)
                    platform_key = self.get_platform_key()
                    self.execute_platform_script(metadata, platform_key)

            def get_mount_point(self):
                root = tk.Tk()
                root.withdraw()  # Hide the root window

                if platform.system().lower() == 'windows':
                    self.mount_point = simpledialog.askstring("Drive Letter", "Enter a drive letter (e.g., Z):", initialvalue="Z")
                    if not self.mount_point:
                        messagebox.showerror("Error", "You must provide a drive letter.")
                        sys.exit(1)
                    self.mount_point = self.mount_point.strip().upper()
                    if len(self.mount_point) != 1 or not self.mount_point.isalpha():
                        messagebox.showerror("Error", "Invalid drive letter. Please enter a valid drive letter.")
                        sys.exit(1)
                else:
                    self.mount_point = filedialog.askdirectory(title="Select Mount Point")
                    if not self.mount_point:
                        messagebox.showerror("Error", "You must select a valid mount point.")
                        sys.exit(1)

            def provision_schema(self, metadata):
                directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
                uuid_dirname_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
                for parent_uuid, children in directory_tree.items():
                    parent_dir = uuid_dirname_mapping.get(parent_uuid)
                    if not parent_dir:
                        continue
                    parent_dir_path = os.path.join(self.mount_point, parent_dir)
                    os.makedirs(parent_dir_path, exist_ok=True)
                    for child in children:
                        child_name = uuid_dirname_mapping.get(child["id"])
                        if child_name:
                            child_dir_path = os.path.join(parent_dir_path, child_name)
                            os.makedirs(child_dir_path, exist_ok=True)

            def execute_platform_script(self, metadata, platform_key):
                platform_scripts = json.loads(metadata.get(b'platform_scripts', '{{}}').decode('utf-8'))
                if platform_key in platform_scripts:
                    row_index = int(platform_scripts[platform_key])
                    script = pq.read_table(self.parquet_path).to_pandas().iloc[row_index, 0]

                    # Replace placeholders in the script
                    script = script.replace("MNTPOINT", self.mount_point)
                    print('Script: ')
                    print(script)
    
                    if platform.system().lower() == 'windows':
                        shell = 'powershell.exe'
                        flag = '-Command'
                    else:
                        shell = '/bin/bash'
                        flag = '-c'

                    try:
                        result = subprocess.run([shell, flag, script], check=True, capture_output=True, text=True)
                        print(f"Stdout: {{result.stdout}}")
                        print(f"Stderr: {{result.stderr}}")
                    except subprocess.CalledProcessError as e:
                        print(f"Script execution failed: {{e}}")
                        print(f"Stdout: {{e.stdout}}")
                        print(f"Stderr: {{e.stderr}}")

            def get_platform_key(self):
                system_platform = platform.system().lower()
                if system_platform == "windows":
                    return "win_script"
                elif system_platform == "darwin":
                    return "darwin_script"
                elif system_platform == "linux":
                    return "linux_script"
                else:
                    raise Exception("Unsupported platform!")

        if __name__ == "__main__":
            provisioner = ParquetProvisioner(r"{parquet_file}")
            provisioner.run()
        """

        # Write the script content to the file with UTF-8 encoding
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(provisioner_script)

        # Read back with UTF-8 encoding
        with open(script_path, 'r', encoding='utf-8') as script_file:
            script_content = script_file.read()

        # Remove unwanted indentation
        script_content = textwrap.dedent(script_content)

        # Write the fixed script back to the file
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)

        return script_path

    def generate_provisioner_script_user(self, parquet_file):
        """
        Generates a Python script with dialogs for username and password.
        """
        # Get the base name of the parquet file (without extension) and current UTC timestamp
        parquet_name = os.path.splitext(os.path.basename(parquet_file))[0]
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        script_name = f"{parquet_name}_{timestamp}.py"

        # Define the target directory to store the script
        target_dir = os.path.join(str(Path.home()), f".aufs/provisioning/pyinstaller/{parquet_name}")
        os.makedirs(target_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # Path for the new Python script
        script_path = os.path.join(target_dir, script_name)

        # Define the provisioning logic script with dialogs for username and password
        provisioner_script = f"""
        import sys
        import os
        import json
        import subprocess
        import platform
        import pyarrow.parquet as pq
        import tkinter as tk
        from tkinter import simpledialog, messagebox

        class ParquetProvisioner:
            def __init__(self, parquet_path):
                self.parquet_path = parquet_path
                self.username = None
                self.password = None

            def run(self):
                parquet_table = pq.read_table(self.parquet_path)
                metadata = parquet_table.schema.metadata

                if metadata:
                    self.get_user_credentials()
                    self.provision_schema(metadata)
                    platform_key = self.get_platform_key()
                    self.execute_platform_script(metadata, platform_key)

            def get_user_credentials(self):
                root = tk.Tk()
                root.withdraw()  # Hide the root window

                self.username = simpledialog.askstring("Username", "Enter your username:")
                self.password = simpledialog.askstring("Password", "Enter your password:", show='*')

            def provision_schema(self, metadata):
                directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
                uuid_dirname_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
                for parent_uuid, children in directory_tree.items():
                    parent_dir = uuid_dirname_mapping.get(parent_uuid)
                    if not parent_dir:
                        continue
                    os.makedirs(parent_dir, exist_ok=True)
                    for child in children:
                        child_name = uuid_dirname_mapping.get(child["id"])
                        if child_name:
                            os.makedirs(child_name, exist_ok=True)

            def execute_platform_script(self, metadata, platform_key):
                platform_scripts = json.loads(metadata.get(b'platform_scripts', '{{}}').decode('utf-8'))
                if platform_key in platform_scripts:
                    row_index = int(platform_scripts[platform_key])
                    script = pq.read_table(self.parquet_path).to_pandas().iloc[row_index, 0]
                    script = script.replace("UNAME", self.username).replace("PSSWD", self.password)

                    if platform.system().lower() == 'windows':
                        shell = 'powershell.exe'
                        flag = '-Command'
                    else:
                        shell = '/bin/bash'
                        flag = '-c'

                    try:
                        result = subprocess.run([shell, flag, script], check=True, capture_output=True, text=True)
                        print(f"Stdout: {{result.stdout}}")
                        print(f"Stderr: {{result.stderr}}")
                    except subprocess.CalledProcessError as e:
                        print(f"Script execution failed: {{e}}")
                        print(f"Stdout: {{e.stdout}}")
                        print(f"Stderr: {{e.stderr}}")

            def get_platform_key(self):
                system_platform = platform.system().lower()
                if system_platform == "windows":
                    return "win_script"
                elif system_platform == "darwin":
                    return "darwin_script"
                elif system_platform == "linux":
                    return "linux_script"
                else:
                    raise Exception("Unsupported platform!")

        if __name__ == "__main__":
            provisioner = ParquetProvisioner(r"{parquet_file}")
            provisioner.run()
        """

        # Write the script content to the file with UTF-8 encoding
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(provisioner_script)

        # Read back with UTF-8 encoding
        with open(script_path, 'r', encoding='utf-8') as script_file:
            script_content = script_file.read()

        # Remove unwanted indentation
        script_content = textwrap.dedent(script_content)

        # Write the fixed script back to the file
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)

        return script_path

    def get_embedded_parquet_path(self, filename):
        """
        Retrieves the full path to the embedded Parquet file.
        """
        if hasattr(sys, '_MEIPASS'):
            # If running from a PyInstaller bundle, look for the Parquet file in the same directory
            base_path = os.path.join(sys._MEIPASS, filename)
        else:
            # Use the local path if running as a script
            base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        return base_path

    def update_spec_file(self, target_parquet_file, provisioner_script):
        """
        Dynamically updates the PyInstaller spec file to include the generated Python script and the copied Parquet file.
        """
        spec_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provisioner.spec")
        
        with open(spec_file_path, 'w') as spec_file:
            spec_file.write(f"""
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{os.path.abspath(provisioner_script)}'],
    pathex=[],
    binaries=[],
    datas=[('{os.path.abspath(target_parquet_file)}', '.')],
    hiddenimports=['pyarrow', 'pyarrow.pandas_compat', 'pyarrow.lib', 'pyarrow.vendored.version', 'pyarrow.vendored', 'numpy', 'tkinter'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='provisioner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
            """)

    def create_double_clickable_package(self):
        """
        Create a double-clickable package from the selected Parquet file using PyInstaller.
        Based on the state of checkboxes, determine which provisioning script to generate.
        """
        selected_item = self.schema_list.currentItem()
        if selected_item:
            source_parquet_file = os.path.join(self.parquet_dir, selected_item.text())  # Full path to the Parquet file

            try:
                # Step 1: Copy the Parquet file to the current working directory (consistent with PyInstaller)
                working_dir = os.getcwd()  # Get the current working directory
                parquet_file = os.path.join(working_dir, os.path.basename(source_parquet_file))
                shutil.copy(source_parquet_file, parquet_file)

                # Step 2: Determine which script to generate based on the checkboxes
                if self.checkbox_credentials.isChecked() and self.checkbox_root_dir.isChecked():
                    # Both credentials and root dir are checked, use full script generation
                    provisioner_script_path = self.generate_provisioner_script(parquet_file)
                elif not self.checkbox_credentials.isChecked() and not self.checkbox_root_dir.isChecked():
                    # All unchecked, generate clean script with no dialogs or replacements
                    provisioner_script_path = self.generate_provisioner_script_clean(parquet_file)
                elif not self.checkbox_root_dir.isChecked():
                    # Mount point unchecked, generate script with only username and password prompts
                    provisioner_script_path = self.generate_provisioner_script_user(parquet_file)
                else:
                    # Only credentials unchecked, generate script with root (mount point) dialog
                    provisioner_script_path = self.generate_provisioner_script_root(parquet_file)

                # Step 3: Run PyInstaller to create an executable package
                self.run_pyinstaller(provisioner_script_path, parquet_file)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create the package: {str(e)}")

    def run_pyinstaller(self, provisioner_script, parquet_file):
        """
        Runs PyInstaller to create an executable from the generated provisioner script.
        :param provisioner_script: Path to the generated Python script.
        :param parquet_file: Path to the selected Parquet file.
        """
        # Make sure the Parquet file is in the current working directory and use its relative path
        parquet_basename = os.path.basename(parquet_file)

        if platform.system().lower() == 'windows':
            add_data = f'{parquet_basename};.'
        else:
            add_data = f'{parquet_basename}:.'

        pyinstaller_command = [
            'pyinstaller',
            '--onefile',                        
            '--add-data', add_data,             # Use relative path for Parquet file
            '--hidden-import', 'pyarrow',       
            '--hidden-import', 'pyarrow.pandas_compat',  
            '--hidden-import', 'pyarrow.lib',   
            '--hidden-import', 'pyarrow.vendored.version',  
            '--hidden-import', 'pyarrow.vendored',  
            '--hidden-import', 'numpy',         
            '--hidden-import', 'tkinter',       
            provisioner_script                 # Script to package
        ]

        try:
            subprocess.run(pyinstaller_command, check=True)
            QMessageBox.information(self, "Success", "Double-clickable package created successfully!")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"PyInstaller failed: {str(e)}")

class AUFSInfoDialog(QDialog):
    def __init__(self, schema, metadata, data, parent=None):
        super().__init__(parent)

        self.setWindowTitle("AUFS Information")

        # Layout
        layout = QVBoxLayout(self)

        # Schema Information
        schema_label = QLabel("Schema:")
        schema_text = QTextEdit()
        schema_text.setReadOnly(True)
        schema_text.setPlainText(str(schema))
        layout.addWidget(schema_label)
        layout.addWidget(schema_text)

        # Metadata Information
        metadata_label = QLabel("Metadata:")
        metadata_text = QTextEdit()
        metadata_text.setReadOnly(True)
        if metadata:
            # Decode the metadata if available (since it's stored as bytes)
            decoded_metadata = {key.decode('utf-8'): val.decode('utf-8') for key, val in metadata.items()}
            metadata_text.setPlainText(json.dumps(decoded_metadata, indent=2))
        else:
            metadata_text.setPlainText("No Metadata")
        layout.addWidget(metadata_label)
        layout.addWidget(metadata_text)

        # Data Information (First Rows)
        data_label = QLabel("Data (First 10 Rows):")
        data_text = QTextEdit()
        data_text.setReadOnly(True)
        data_text.setPlainText(str(data.head(10)))  # Show the first 10 rows
        layout.addWidget(data_label)
        layout.addWidget(data_text)

        # Close Button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AUFS()
    window.show()
    sys.exit(app.exec())
