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
            self.get_mount_point()  # Prompt user for the mount point
            self.provision_schema(metadata)  # Create directory tree based on metadata
            platform_key = self.get_platform_key()  # Identify OS-specific key
            self.execute_platform_script(metadata, platform_key)  # Run any platform-specific script

    def get_mount_point(self):
        root = tk.Tk()
        root.withdraw()  # Hide the root windo
        self.mount_point = filedialog.askdirectory(title="Select Mount Point")
        if not self.mount_point:
            messagebox.showerror("Error", "You must select a valid mount point.")
            sys.exit(1)

    def provision_schema(self, metadata):
        directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
        uuid_dirname_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))

        # Create a dictionary to track full paths to avoid duplications
        full_paths = {}

        for parent_uuid, children in directory_tree.items():
            parent_dir = uuid_dirname_mapping.get(parent_uuid)

            if not parent_dir:
                continue

            # Get or create the full path for the parent directory
            if parent_uuid not in full_paths:
                parent_dir_path = os.path.join(self.mount_point, parent_dir)
                full_paths[parent_uuid] = parent_dir_path
                os.makedirs(parent_dir_path, exist_ok=True)

            # Now process the children directories
            for child in children:
                child_name = uuid_dirname_mapping.get(child["id"])

                if child_name:
                    # Build the full path for the child directory
                    child_dir_path = os.path.join(full_paths[parent_uuid], child_name)
                    full_paths[child["id"]] = child_dir_path
                    os.makedirs(child_dir_path, exist_ok=True)

            print(f"Processed {parent_dir} -> {children}")

    def execute_platform_script(self, metadata, platform_key):
        # Execute the platform-specific script after provisioning the directory structure.
        
        platform_scripts = json.loads(metadata.get(b'platform_scripts', '{{}}').decode('utf-8'))
        if platform_key in platform_scripts:
            row_index = int(platform_scripts[platform_key])
            script = pq.read_table(self.parquet_path).to_pandas().iloc[row_index, 0]
            # Replace placeholder with the actual mount point
            script = script.replace("MNTPOINT", self.mount_point)
            print('Executing script:')
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
        # Identify the current operating system and return the appropriate script key
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
    # Check if a Parquet file path is passed as a command-line argument
    if len(sys.argv) > 1:
        parquet_file_path = sys.argv[1]  # Take the first argument as the Parquet file path
    else:
        messagebox.showerror("Error", "Please provide a Parquet file path as a command-line argument.")
        sys.exit(1)  # Exit if no argument is provide
    provisioner = ParquetProvisioner(parquet_file_path)
    provisioner.run()