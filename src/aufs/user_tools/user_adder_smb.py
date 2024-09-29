import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QCheckBox
)
from pathlib import Path
import pandas as pd
from PySide6.QtCore import Slot, Qt
import paramiko
import csv
import random
import string

class SMBUserAdder(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()

        # PEM file input
        self.pem_file_label = QLabel("Select PEM/Credentials File:")
        self.pem_file_input = QLineEdit(self)
        self.pem_file_input.setText("G:/scratch/uel/aws_temp/euw2-workstations.pem")
        self.pem_file_browse = QPushButton("Browse", self)
        self.pem_file_browse.clicked.connect(self.browse_pem_file)

        layout.addWidget(self.pem_file_label)
        layout.addWidget(self.pem_file_input)
        layout.addWidget(self.pem_file_browse)

        # SSH user input
        self.ssh_user_label = QLabel("SSH Non-Root Username:")
        self.ssh_user_input = QLineEdit(self)
        self.ssh_user_input.setText("ec2-user")

        layout.addWidget(self.ssh_user_label)
        layout.addWidget(self.ssh_user_input)

        # Server IP input
        self.server_ip_label = QLabel("Server IP Address:")
        self.server_ip_input = QLineEdit(self)
        self.server_ip_input.setText("18.175.206.107")

        layout.addWidget(self.server_ip_label)
        layout.addWidget(self.server_ip_input)

        # Path to user directories
        self.user_dirs_label = QLabel("Path to User Directories:")
        self.user_dirs_input = QLineEdit(self)
        self.user_dirs_input.setText("/mnt/deadline-london/data/aufs")

        layout.addWidget(self.user_dirs_label)
        layout.addWidget(self.user_dirs_input)

        # Individual User Input (Name, Username, Password)
        self.name_label = QLabel("User's Name:")
        self.name_input = QLineEdit(self)
        self.name_input.setText("Uel Hormann")

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit(self)
        self.username_input.setText("uel")

        # Password Input and Generation
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit(self)
        self.password_generate = QPushButton("Generate Password", self)
        self.password_generate.clicked.connect(self.generate_random_password)

        # Safe mode checkbox
        self.safe_mode_checkbox = QCheckBox("Safe Mode (alphanumeric only)", self)
        self.safe_mode_checkbox.setChecked(True)
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.password_generate)
        layout.addWidget(self.safe_mode_checkbox)

        # CSV file input
        self.csv_file_label = QLabel("Select CSV File:")
        self.csv_file_input = QLineEdit(self)
        self.csv_file_browse = QPushButton("Browse", self)
        self.csv_file_browse.clicked.connect(self.browse_csv_file)

        layout.addWidget(self.csv_file_label)
        layout.addWidget(self.csv_file_input)
        layout.addWidget(self.csv_file_browse)

        # Action buttons
        self.add_button = QPushButton("Do It!", self)
        self.add_button.clicked.connect(self.process_users)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.close)

        layout.addWidget(self.add_button)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)
        self.setWindowTitle("SMB User Adder")

    def generate_random_password(self):
        """Generate a strong random password, optionally in safe mode."""
        password_length = 12

        # Check if safe mode is enabled
        if self.safe_mode_checkbox.isChecked():
            characters = string.ascii_letters + string.digits
        else:
            # Full set of characters minus blacklisted ones
            blacklist = ":;?~|<>"
            characters = ''.join(c for c in (string.ascii_letters + string.digits + string.punctuation) if c not in blacklist)

        # Generate the random password
        random_password = ''.join(random.choice(characters) for _ in range(password_length))
        self.password_input.setText(random_password)

    @Slot()
    def browse_pem_file(self):
        pem_file, _ = QFileDialog.getOpenFileName(self, "Select PEM File", "", "PEM Files (*.pem)")
        if pem_file:
            self.pem_file_input.setText(pem_file)

    @Slot()
    def browse_csv_file(self):
        csv_file, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if csv_file:
            self.csv_file_input.setText(csv_file)

    @Slot()
    def process_users(self):
        # Collect all inputs
        pem_file = self.pem_file_input.text()
        ssh_user = self.ssh_user_input.text()
        server_ip = self.server_ip_input.text()
        user_dirs = self.user_dirs_input.text()

        name = self.name_input.text()
        username = self.username_input.text()
        password = self.password_input.text()

        csv_file = self.csv_file_input.text()

        if csv_file and not (name and username and password):
            self.process_csv_users(pem_file, ssh_user, server_ip, user_dirs, csv_file)
        elif name and username and password:
            self.add_user_via_ssh(pem_file, ssh_user, server_ip, user_dirs, name, username, password)
        else:
            QMessageBox.warning(self, "Input Error", "Please provide either a CSV file or manual user input.")

    def process_csv_users(self, pem_file, ssh_user, server_ip, user_dirs, csv_file):
        # Open the CSV file and extract user details
        with open(csv_file, newline='') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip the header row
            for row in reader:
                name, user_data = row[0], row[1]
                username, password = user_data.split(':')
                self.add_user_via_ssh(pem_file, ssh_user, server_ip, user_dirs, name, username, password)

    def add_user_via_ssh(self, pem_file, ssh_user, server_ip, user_dirs, name, username, password):
        try:
            # Connect to the server via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(server_ip, username=ssh_user, key_filename=pem_file)

            # Step 1: Add user (skip if user already exists)
            adduser_cmd = f"sudo adduser -m {username}"
            stdin, stdout, stderr = ssh.exec_command(adduser_cmd)
            adduser_error = stderr.read().decode('utf-8').strip()

            if "already exists" in adduser_error:
                print(f"User {username} already exists, skipping adduser.")
            elif adduser_error:
                print(f"Error adding user {username}: {adduser_error}")
            else:
                print(f"User {username} added successfully.")

            # Step 2: Copy the default directory (skip if already exists)
            cp_cmd = f"sudo cp -r {user_dirs}/.default {user_dirs}/{username}"
            stdin, stdout, stderr = ssh.exec_command(cp_cmd)
            cp_error = stderr.read().decode('utf-8').strip()

            if cp_error:
                print(f"Error copying default directory for {username}: {cp_error}")
            else:
                print(f"Directory copied for user {username}.")

            # Step 2.5: Create identifier file
            touch_cmd = f"sudo touch {user_dirs}/{username}/.{username}_data"
            stdin, stdout, stderr = ssh.exec_command(touch_cmd)
            touch_error = stderr.read().decode('utf-8').strip()

            if touch_error:
                print(f"Error creating identifier for {username}: {touch_error}")
            else:
                print(f"Identifier created for {username}.")

            # Step 3: Change ownership of the directory (always run this)
            chown_cmd = f"sudo chown -R {username}:{username} {user_dirs}/{username}"
            stdin, stdout, stderr = ssh.exec_command(chown_cmd)
            chown_error = stderr.read().decode('utf-8').strip()

            if chown_error:
                print(f"Error changing ownership for {username}: {chown_error}")
            else:
                print(f"Ownership changed for {username}.")

            # Step 4: Set SMB password
            smbpasswd_cmd = f"echo -e \"{password}\\n{password}\" | sudo smbpasswd -a {username}"
            stdin, stdout, stderr = ssh.exec_command(smbpasswd_cmd)
            smbpasswd_error = stderr.read().decode('utf-8').strip()

            if smbpasswd_error:
                print(f"Error setting SMB password for {username}: {smbpasswd_error}")
            else:
                print(f"SMB password set for {username}.")

            # Step 4.5: Append the SMB share to smb.conf
            share_config = f"""
[{username}_data]
path = {user_dirs}/{username}
read only = no
valid users = {username}
            """
            check_cmd = f"grep '\\[{username}_data\\]' /etc/samba/smb.conf"
            stdin, stdout, stderr = ssh.exec_command(check_cmd)
            check_output = stdout.read().decode('utf-8').strip()

            if not check_output:
                # Append only if the share does not exist
                append_cmd = f"echo '{share_config}' | sudo tee -a /etc/samba/smb.conf"
                stdin, stdout, stderr = ssh.exec_command(append_cmd)
                append_error = stderr.read().decode('utf-8').strip()

                if append_error:
                    print(f"Error appending share for {username} to smb.conf: {append_error}")
                else:
                    print(f"Share for {username} appended to smb.conf.")

                # Reload Samba to apply the new share
                reload_cmd = "sudo systemctl reload smbd"
                stdin, stdout, stderr = ssh.exec_command(reload_cmd)
                reload_error = stderr.read().decode('utf-8').strip()

                if reload_error:
                    print(f"Error reloading SMB service: {reload_error}")
                else:
                    print(f"SMB service reloaded successfully.")
            else:
                print(f"SMB share for {username} already exists in smb.conf, skipping.")

            # Step 5: Restart the SMB service
            restart_cmd = "sudo systemctl restart smb.service"
            stdin, stdout, stderr = ssh.exec_command(restart_cmd)
            restart_error = stderr.read().decode('utf-8').strip()

            if restart_error:
                print(f"Error restarting SMB service: {restart_error}")
            else:
                print(f"SMB service restarted successfully.")

            # Step 6: Append the user to aufs_smb_users.csv
            self.append_to_csv(username, password, name)

            ssh.close()
            QMessageBox.information(self, "Success", f"User {username} added successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add user {username}. Error: {str(e)}")
            print(f"Error: {str(e)}")

    def append_to_csv(self, username, password, name):
        try:
            # Define the file and directory paths
            csv_file_path = Path.home() / ".aufs/provisioning/users/smb/aufs_smb_users.csv"
            csv_dir = csv_file_path.parent

            # Ensure the directory exists (create if not)
            if not csv_dir.exists():
                print(f"Directory {csv_dir} does not exist, creating it.")
                csv_dir.mkdir(parents=True, exist_ok=True)
                print(f"Directory {csv_dir} created.")

            # Check if the CSV file exists
            if not csv_file_path.exists():
                print(f"CSV file {csv_file_path} does not exist, creating it.")

                # Create a new DataFrame with the user's data
                df = pd.DataFrame({name: [f"{username}:{password}"]})
                df.to_csv(csv_file_path, index=False)

                print(f"New CSV file created and user {username} added to {csv_file_path}")
                QMessageBox.information(self, "CSV Created", f"CSV file {csv_file_path} created successfully.")
            else:
                # Load the existing CSV into a DataFrame
                df = pd.read_csv(csv_file_path)

                # Create a new column with "User's Name" as the header and "username:password" as the value
                new_user_column = pd.Series([f"{username}:{password}"], index=df.index)
                df[name] = new_user_column

                # Write the updated DataFrame back to the CSV file
                df.to_csv(csv_file_path, index=False)
                print(f"User {username} added to {csv_file_path}")

        except Exception as e:
            print(f"Error appending user to CSV: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to append user to CSV file. Error: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SMBUserAdder()
    window.show()
    sys.exit(app.exec())
