import os
import subprocess
import configparser
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QInputDialog, 
                               QComboBox, QCheckBox, QFileDialog, QTextEdit, QWidget, QFormLayout, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt

class EnvConfigUtility(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ObjectiveFS Env Config Utility")
        self.setGeometry(100, 100, 800, 600)
        
        self.is_new_config = False
        self.loaded_env_dir = None  # To track loaded env directory for saving later

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)
        
        # Load, New, Save, and Save As Buttons
        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Env Directory")
        self.load_button.clicked.connect(self.load_env_directory)
        self.new_button = QPushButton("New Ofs Config")
        self.new_button.clicked.connect(self.new_env_directory)
        self.save_button = QPushButton("Save Config")
        self.save_button.clicked.connect(self.save_env_config)
        self.save_button.setEnabled(False)  # Disabled until config is loaded or created
        self.save_as_button = QPushButton("Save Config As")
        self.save_as_button.clicked.connect(self.save_env_config_as)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.save_as_button)
        main_layout.addLayout(button_layout)

        # Environment Variable Inputs
        default_vars_layout = QFormLayout()
        self.access_key_input = self.create_larger_input("ACCESS_KEY (AWS Key):", default_vars_layout)
        self.secret_key_input = self.create_larger_input("SECRET_KEY (AWS Secret Key):", default_vars_layout)
        self.region_dropdown = self.create_larger_dropdown("REGION:", ['eu-west-2', 'us-east-1', 'us-west-1', 'eu-west-1', 'ap-south-1'], default_vars_layout)
        self.objectstore_dropdown = self.create_larger_dropdown("OBJECTSTORE:", ['s3://', 'wasabi://', 'gs://', 'ocs://'], default_vars_layout)
        self.license_input = self.create_larger_input("OBJECTIVEFS_LICENSE:", default_vars_layout)
        self.passphrase_input = self.create_larger_input("OBJECTIVEFS_PASSPHRASE:", default_vars_layout)
        self.cache_size_input = self.create_larger_input("CACHESIZE (% or GB/MB):", default_vars_layout)
        self.diskcache_size_input = self.create_larger_input("DISKCACHE_SIZE (% or GB/MB):", default_vars_layout)
        self.diskcache_path_input = self.create_larger_input("DISKCACHE_PATH:", default_vars_layout)

        # AWS Transfer Acceleration Checkbox
        self.acceleration_checkbox = QCheckBox("Enable Transfer Acceleration")
        self.acceleration_checkbox.setFixedHeight(30)
        default_vars_layout.addRow(QLabel("AWS_TRANSFER_ACCELERATION:"), self.acceleration_checkbox)
        main_layout.addLayout(default_vars_layout)

        # Advanced Variables (Initially Hidden)
        self.advanced_vars_groupbox = QGroupBox("Advanced Variables (Click to Expand)")
        self.advanced_vars_groupbox.setCheckable(True)
        self.advanced_vars_groupbox.setChecked(False)
        self.advanced_vars_groupbox.toggled.connect(self.toggle_advanced_vars)
        advanced_vars_layout = QVBoxLayout()
        self.advanced_var_1 = self.create_larger_input("Advanced Variable 1:", advanced_vars_layout, form_layout=False)
        self.advanced_var_2 = self.create_larger_input("Advanced Variable 2:", advanced_vars_layout, form_layout=False)
        self.advanced_vars_groupbox.setLayout(advanced_vars_layout)
        main_layout.addWidget(self.advanced_vars_groupbox)

        # Process Output Pane
        self.output_pane = QTextEdit()
        self.output_pane.setReadOnly(True)
        main_layout.addWidget(self.output_pane)

        # Create Filesystem Button
        self.create_fs_button = QPushButton("Create Filesystem")
        self.create_fs_button.clicked.connect(self.create_filesystem)
        main_layout.addWidget(self.create_fs_button)

    def create_larger_input(self, label_text, layout, form_layout=True):
        label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setFixedHeight(30)
        line_edit.setFixedWidth(350)
        if form_layout:
            layout.addRow(label, line_edit)
        else:
            layout.addWidget(label)
            layout.addWidget(line_edit)
        return line_edit

    def create_larger_dropdown(self, label_text, options, layout):
        label = QLabel(label_text)
        dropdown = QComboBox()
        dropdown.addItems(options)
        dropdown.setFixedHeight(30)
        dropdown.setFixedWidth(350)
        layout.addRow(label, dropdown)
        return dropdown

    def save_env_config_as(self):
        """Save environment configuration to a user-selected directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory to Save Config As")
        if directory:
            self.save_env_variables(directory)
            QMessageBox.information(self, "Save Config As", "Config saved successfully to new location!")

    def save_env_config(self):
        """Save the environment config to a directory."""
        if self.is_new_config:
            self.save_env_config_as()
        else:
            self.save_env_variables(self.loaded_env_dir)
            QMessageBox.information(self, "Save Config", "Config saved successfully!")

    def save_env_variables(self, directory):
        """Save the environment variables to flat files in the specified directory with correct permissions."""
        # Set permissions for the parent directory once
        set_permissions(directory, 0o700)
        
        # Iterate over environment variables and save each one
        for key, widget in self.get_variable_map().items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
            elif isinstance(widget, QComboBox):
                value = widget.currentText().strip()
            file_path = os.path.join(directory, key)

            try:
                # Write the variable to the file and set it to read-only (400)
                with open(file_path, 'w') as f:
                    f.write(value)
                set_permissions(file_path, 0o400)
                self.output_pane.append(f"Saved {key} to {file_path} with 400 permissions.\n")
            except PermissionError:
                self.output_pane.append(f"Failed to save {key}: Permission denied.\n")
            except Exception as e:
                self.output_pane.append(f"Failed to save {key}: {e}\n")

    def load_env_directory(self):
        """Load existing environment directory and populate fields."""
        self.reset_form()
        directory = QFileDialog.getExistingDirectory(self, "Select Env Directory")
        if directory:
            self.output_pane.append(f"Loading environment directory: {directory}\n")
            self.loaded_env_dir = directory
            self.is_new_config = False
            self.save_button.setEnabled(True)  # Enable the save button
            
            # Load the environment variables from the flat files and populate fields
            for key, widget in self.get_variable_map().items():
                file_path = os.path.join(directory, key)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        value = f.read().strip()
                        if isinstance(widget, QLineEdit):
                            widget.setText(value)
                        elif isinstance(widget, QComboBox):
                            index = widget.findText(value)
                            if index >= 0:
                                widget.setCurrentIndex(index)
            self.output_pane.append("Environment variables loaded.\n")

    def reset_form(self):
        """Clear all inputs but do not run the AWS credentials check."""
        for widget in self.get_variable_map().values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
        self.acceleration_checkbox.setChecked(False)

    def get_variable_map(self):
        """Return a map of environment variable names to their corresponding input fields."""
        return {
            "ACCESS_KEY": self.access_key_input,
            "SECRET_KEY": self.secret_key_input,
            "REGION": self.region_dropdown,
            "OBJECTSTORE": self.objectstore_dropdown,
            "OBJECTIVEFS_LICENSE": self.license_input,
            "OBJECTIVEFS_PASSPHRASE": self.passphrase_input,
            "CACHESIZE": self.cache_size_input,
            "DISKCACHE_SIZE": self.diskcache_size_input,
            "DISKCACHE_PATH": self.diskcache_path_input,
        }

    def create_filesystem(self):
        """
        Handles the 'Create Filesystem' button click.
        Prompts for filesystem name and uses it as both filesystem and bucket name, then calls `create_filesystem`.
        """
        if not self.loaded_env_dir:
            QMessageBox.warning(self, "Filesystem Creation", "Please load or create an environment configuration first.")
            return

        # Prompt for filesystem name (used as bucket name too)
        filesystem_name, ok_name = QInputDialog.getText(self, "Enter Filesystem Name", "Filesystem Name (used as bucket name):")
        if not ok_name or not filesystem_name:
            self.output_pane.append("Filesystem creation canceled.\n")
            return

        # Validate filesystem name syntax
        valid_name, message = validate_filesystem_name(filesystem_name)
        if not valid_name:
            QMessageBox.warning(self, "Invalid Name", message)
            self.output_pane.append(f"Invalid filesystem name: {message}\n")
            return

        # Create filesystem using the name as both the filesystem and bucket name
        success = create_filesystem(self.loaded_env_dir, filesystem_name, filesystem_name)
        if success:
            self.output_pane.append(f"Filesystem '{filesystem_name}' created successfully as bucket '{filesystem_name}'.\n")
        else:
            self.output_pane.append(f"Failed to create filesystem '{filesystem_name}'. Check log for details.\n")

    def check_aws_credentials(self):
        """Check ~/.aws/credentials for available AWS credentials and autofill."""
        aws_creds_file = os.path.expanduser("~/.aws/credentials")
        if os.path.exists(aws_creds_file):
            config = configparser.ConfigParser()
            config.read(aws_creds_file)
            if 'default' in config:
                access_key = config.get('default', 'aws_access_key_id', fallback=None)
                secret_key = config.get('default', 'aws_secret_access_key', fallback=None)
                if access_key:
                    self.access_key_input.setText(access_key)
                if secret_key:
                    self.secret_key_input.setText(secret_key)
            self.output_pane.append("AWS credentials loaded from ~/.aws/credentials\n")

    def new_env_directory(self):
        """Reset the form to allow creation of new env config."""
        self.clear_form()
        self.is_new_config = True
        self.save_button.setEnabled(True)  # Enable the save button
        self.output_pane.append("Creating a new environment configuration...\n")

    def clear_form(self):
        """Clear all inputs and run the AWS credentials check."""
        self.reset_form()  # Use the new reset_form method to clear the form
        self.check_aws_credentials()  # Then, run the credentials check

    def toggle_advanced_vars(self, checked):
        """Toggle visibility of advanced variables."""
        if checked:
            self.advanced_vars_groupbox.setTitle("Advanced Variables (Expanded)")
        else:
            self.advanced_vars_groupbox.setTitle("Advanced Variables (Collapsed)")

def set_permissions(file_path, mode):
    """Set permissions using chmod."""
    if not os.path.exists(file_path):
        return
    
    mode_str = oct(mode)[2:]
    try:
        subprocess.run(['chmod', mode_str, file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to set permissions for {file_path}: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnvConfigUtility()
    window.show()
    sys.exit(app.exec())
