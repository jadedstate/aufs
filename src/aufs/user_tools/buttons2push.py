import sys
import os
import platform
import subprocess
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QMenu,
    QWidget, QFileDialog, QMessageBox, QMenuBar, QHBoxLayout,
    QToolButton, QLabel, QGridLayout, QFrame
)
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Python Script Launcher')
        self.setGeometry(100, 100, 500, 300)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.button_pane = QWidget()
        self.button_pane_layout = QVBoxLayout(self.button_pane)
        self.main_layout.addWidget(self.button_pane, 75)  # Allocate 75% to the main app space

        self.setup_bottom_panel()
        self.setup_menubar()

        self.config_path = os.path.expanduser('~/.aufs/config/user_config.csv')
        self.ensure_config_exists()

    def ensure_config_exists(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            self.ask_for_discovery_paths()
        else:
            self.refresh_config()

    def ask_for_discovery_paths(self):
        path = QFileDialog.getExistingDirectory(self, "Select Discovery Path")
        if path:
            df = pd.DataFrame(columns=['DiscoveryPaths', 'Name', 'Status', 'Set', 'Order', 'Path', 'Silent'])
            df.loc[0, ['DiscoveryPaths', 'Silent']] = [path, 'yes']
            df.to_csv(self.config_path, index=False)
            self.refresh_config()

    def refresh_config(self):
        df = pd.read_csv(self.config_path)
        self.update_config_based_on_discovery_paths(df)
        self.setup_interface()

    def has_gui_framework(self, filepath):
        """Check if the file contains 'PySide6' or 'PyQt5' in the first part of the file."""
        try:
            with open(filepath, 'r') as file:
                for line in file:
                    # Convert line to lower case to ensure case insensitive matching
                    line_lower = line.lower()
                    if 'pyside6' in line_lower or 'pyqt5' in line_lower or 'flask' in line_lower:
                        return True
                    if 'class' in line_lower or 'def' in line_lower:
                        break
        except Exception as e:
            print(f"Failed to read {filepath}: {e}")
        return False

    def update_config_based_on_discovery_paths(self, df):
        all_files = set()
        for path in df['DiscoveryPaths'].dropna().unique():
            if os.path.isdir(path):
                all_files.update({os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))})

        current_files = set(df['Path'].dropna().unique())
        new_entries = False

        if 'Set' in df.columns:
            df['Set'] = df['Set'].fillna('')
            df['Set'] = df['Set'].astype(str)
        else:
            df['Set'] = ''

        new_files_data = []
        for new_file in all_files - current_files:
            if self.has_gui_framework(new_file):  # Check if the file contains the GUI framework
                new_entries = True
                new_order = df[df['Set'].str.startswith('Unused')]['Order'].max() + 1 if not df[df['Set'].str.startswith('Unused')].empty else 1
                new_files_data.append({
                    'DiscoveryPaths': '',
                    'Name': os.path.basename(new_file),
                    'Status': 'inactive',
                    'Set': 'Unused-01',
                    'Order': new_order,
                    'Path': new_file
                })

        if new_files_data:
            df = pd.concat([df, pd.DataFrame(new_files_data)], ignore_index=True)

        df.to_csv(self.config_path, index=False)
        if new_entries:
            QMessageBox.information(self, "Configuration Update", "New items added to your Config.")

    def connect_tool_button(self, tool_button, path, child_actions=[]):
        def on_tool_button_clicked():
            self.launch_script(path)

        tool_button.clicked.connect(on_tool_button_clicked)

        if child_actions:
            menu = QMenu()
            for action_path, action_name in child_actions:
                action = QAction(action_name, self)
                self.setup_action(action, action_path)
                menu.addAction(action)

            tool_button.setMenu(menu)
            tool_button.setPopupMode(QToolButton.MenuButtonPopup)

    def setup_action(self, action, path):
        """Connect QAction to a method to execute the script."""
        def trigger_action():
            self.launch_script(path)
        
        action.triggered.connect(trigger_action)

    def setup_interface(self):
        df = pd.read_csv(self.config_path)
        df = df[df['Status'] == 'active']
        df.sort_values(by=['Set', 'Order'], inplace=True)

        window_df = df[df['Path'].isnull()]
        button_df = df[df['Set'].isin(window_df['Name']) & df['Path'].notnull()]
        item_df = df[~df['Set'].isin(window_df['Name']) & df['Path'].notnull()]

        # Clearing the current layout
        while self.button_pane_layout.count():
            item = self.button_pane_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Setting up windows and tool buttons
        for i, (index, win) in enumerate(window_df.iterrows()):
            window_widget = QWidget()
            window_layout = QGridLayout(window_widget)

            # Label for the window's name
            window_label = QLabel(win['Name'])
            window_label.setAlignment(Qt.AlignCenter)
            window_layout.addWidget(window_label, 0, 0, 1, 4)  # Span across the first row

            buttons = button_df[button_df['Set'] == win['Name']]
            for j, (_, btn) in enumerate(buttons.iterrows()):
                row = (j // 4) + 1  # Start on the second row, increment every 4 buttons
                col = j % 4
                tool_button = QToolButton()
                tool_button.setText(btn['Name'])
                child_actions = [(item['Path'], item['Name']) for _, item in item_df[item_df['Set'] == btn['Name']].iterrows()]
                self.connect_tool_button(tool_button, btn['Path'], child_actions)
                window_layout.addWidget(tool_button, row, col)

            # Calculate the next row number after all buttons are placed
            next_row = (len(buttons) // 4) + 1 if len(buttons) % 4 != 0 else len(buttons) // 4
            next_row += 1  # This ensures that the line is placed after the last row of buttons
            
            # Add a grey line after the last row of buttons
            line = self.create_horizontal_line()
            window_layout.addWidget(line, next_row, 0, 1, 4)  # Span across the last row of buttons

            self.button_pane_layout.addWidget(window_widget)

    def create_horizontal_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        palette = line.palette()
        palette.setColor(QPalette.WindowText, QColor('grey'))
        line.setPalette(palette)
        return line
                
    def connect_button(self, button, path):
        def on_button_clicked(checked):
            self.launch_script(path)
        button.clicked.connect(on_button_clicked)

    def connect_action(self, action, path):
        def on_action_triggered(checked):
            self.launch_script(path)
        action.triggered.connect(on_action_triggered)

    def launch_script(self, script_path):
        # Determine the base name of the script to be launched
        script_name = os.path.basename(script_path)

        # Ensure we're using the correct Python executable from the virtual environment
        python_executable = sys.executable

        # Determine the appropriate command and working directory based on the script name
        if script_name == 'io_dir_monitor_v02.py':
            # Use the helper script for 'io_dir_monitor_v02.py'
            helper_script_dir = os.path.dirname(__file__)  # Assuming this script is in the same directory as the buttons app
            helper_script_path = os.path.join(helper_script_dir, 'io_dir_monitor_runner.py')
            command = [python_executable, helper_script_path]
            working_directory = os.path.dirname(helper_script_path)
        elif script_name == 'aws_ec2_instances_01.py':
            # Special case for 'aws_ec2_instances_01.py'
            # Set working directory to the base of the `utils` directory
            working_directory = os.path.abspath(os.path.join(os.path.dirname(script_path), '../../'))
            command = [python_executable, script_path]
        else:
            # Run other scripts directly
            command = [python_executable, script_path]
            working_directory = os.path.dirname(script_path)

        # Debug: print the command and the working directory
        print(f'Running command: {" ".join(command)}')
        print(f'Working directory: {working_directory}')

        # Read the config to determine if the script should run silently or not
        df = pd.read_csv(self.config_path)
        script_info = df[df['Path'] == script_path]

        silent = script_info.empty or script_info.iloc[0]['Silent'] == 'yes'

        if platform.system() == 'Windows':
            if silent:
                subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=working_directory)
            else:
                subprocess.Popen(['start', '/wait', 'cmd', '/c', ' '.join(command)], shell=True, cwd=working_directory)

        elif platform.system() == 'Darwin':
            if silent:
                subprocess.Popen(command, start_new_session=True, cwd=working_directory)
            else:
                # Construct the AppleScript command for macOS to open in a new Terminal window
                apple_script_command = f'tell application "Terminal" to do script "cd {working_directory} && {" ".join(command)}"'
                subprocess.Popen(['osascript', '-e', apple_script_command], start_new_session=True)

        elif platform.system() == 'Linux':
            if silent:
                subprocess.Popen(command, start_new_session=True, cwd=working_directory)
            else:
                # Open in a new GNOME Terminal window on Linux
                terminal_command = f'gnome-terminal -- bash -c "cd {working_directory} && {" ".join(command)}; exec bash"'
                subprocess.Popen(terminal_command, shell=True, start_new_session=True, cwd=working_directory)
            
    def setup_bottom_panel(self):
        bottom_panel = QWidget()
        bottom_panel_layout = QHBoxLayout(bottom_panel)
        self.main_layout.addWidget(bottom_panel, 25)
        refresh_button = QPushButton("Refresh Layout")
        refresh_button.clicked.connect(self.refresh_config)
        bottom_panel_layout.addWidget(refresh_button)
        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(sys.exit)
        bottom_panel_layout.addWidget(exit_button)

    def setup_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        open_action = QAction('Preferences', self)
        open_action.triggered.connect(self.open_preferences)
        file_menu.addAction(open_action)

    def open_preferences(self):
        if sys.platform.startswith('linux'):
            subprocess.call(['xdg-open', self.config_path])
        elif sys.platform.startswith('win'):
            os.startfile(self.config_path)
        elif sys.platform.startswith('darwin'):
            subprocess.call(['open', self.config_path])

    def launch_window(self, name):
        print(f"Window '{name}' launched.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = Launcher()
    mainWin.show()
    sys.exit(app.exec())
