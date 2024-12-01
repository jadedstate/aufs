import sys
import platform
import os
import pandas as pd
import json
import subprocess
from PySide6.QtCore import QUrl, Slot, Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QPushButton
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from jinja2 import Environment, FileSystemLoader

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.fs_meta.aws_data_manager import AwsDataManager
from src.aufs.user_tools.action.grid_action_handler import gridActionHandler
from src.aufs.user_tools.action.ec2_list_input_dialog import TextInputDialog
from src.aufs.user_tools.fs_meta.aws_ec2_manager import AwsEC2Manager
from src.aufs.user_tools.fs_meta.files_paths import set_a_render_root_for_os

class DataProvider(QWidget):
    def __init__(self):
        super().__init__()
        self.root_os = set_a_render_root_for_os('R:/')
        self.action_handler = gridActionHandler()
        self.aws_data_manager = AwsDataManager()
        self.ec2_regions = [
            'eu-west-2', 'eu-west-1', 'ap-south-1',
            'eu-north-1', 'ap-northeast-1', 'ap-northeast-2',
            'us-east-1', 'us-west-2', 'ap-south-2'
        ]
        self.render_group_filter = 'all'
        self.parquet_file_path = os.path.join(self.root_os, 'dsvfx/render/main/ec2_instance_data.parquet')

    @Slot(str, result=str)
    def setRenderGroupFilter(self, filter_type):
        self.render_group_filter = filter_type
        return json.dumps({'status': 'success', 'filter_type': self.render_group_filter})

    @Slot(result=str)
    def getData(self):
        # Load the data from the Parquet file
        df = pd.read_parquet(self.parquet_file_path)

        # Apply filtering logic
        if not df.empty:
            df.columns = df.columns.str.replace('.', '_')

            if self.render_group_filter == 'withRenderGroup':
                # Keep rows where 'RenderGroup' is valid (truthy)
                df = df[df['RenderGroup'].apply(bool)]
            elif self.render_group_filter == 'withoutRenderGroup':
                # Keep rows where 'RenderGroup' is missing or not set (falsy)
                df = df[~df['RenderGroup'].apply(bool)]

        return df.to_json(orient='records')

    @Slot(str, str, result=str)
    def handleAction(self, action, payload):
        try:
            data = json.loads(payload)
            response = self.action_handler.process_action(action, data)
            return response
        except Exception as e:
            print(f"Error handling action {action}: {e}")
            return json.dumps({'status': 'error', 'message': str(e)})

class MainWindow(QMainWindow):
    def __init__(self, directory=None):
        super().__init__()
        self.setWindowTitle("EC2 Instance Monitor")
        self.setGeometry(100, 100, 1200, 1400)

        self.data_provider = DataProvider()
        self.layout = QVBoxLayout()

        self.browser = QWebEngineView()
        self.channel = QWebChannel()
        self.browser.page().setWebChannel(self.channel)
        self.channel.registerObject("dataProvider", self.data_provider)

        self.setup_ui()
        self.load_html()

        if directory:
            self.load_directory(directory)

    def setup_ui(self):
        container = QWidget()
        container.setFixedHeight(50)

        self.render_group_combo_box = QComboBox(self)
        self.render_group_combo_box.addItems(["Show All", "Show with RenderGroup", "Show without RenderGroup"])
        self.render_group_combo_box.currentIndexChanged.connect(self.toggle_render_group_filter)

        self.input_dialog_button = QPushButton("K-List Input Dialog", self)
        self.input_dialog_button.clicked.connect(lambda: self.launch_input_dialog('terminate'))

        self.cleanup_dialog_button = QPushButton("Clean Up Input Dialog", self)
        self.cleanup_dialog_button.clicked.connect(lambda: self.launch_input_dialog('cleanup'))

        # Add the new button to launch ec2_instance_parquet_writer.py
        self.launch_writer_button = QPushButton("Launch EC2 Info Fetcher", self)
        self.launch_writer_button.clicked.connect(self.launch_parquet_writer)

        top_layout = QVBoxLayout()
        self.top_button_layout = QHBoxLayout()
        self.top_button_layout.addWidget(self.render_group_combo_box)
        self.top_button_layout.addWidget(self.input_dialog_button)
        self.top_button_layout.addWidget(self.cleanup_dialog_button)
        self.top_button_layout.addWidget(self.launch_writer_button)  # Add the new button to the layout

        top_layout.addLayout(self.top_button_layout)
        container.setLayout(top_layout)

        self.layout.addWidget(container)
        self.layout.addWidget(self.browser)

        main_widget = QWidget()
        main_widget.setLayout(self.layout)
        self.setCentralWidget(main_widget)

    def launch_input_dialog(self, mode):
        dialog = TextInputDialog(
            data_manager=self.data_provider.aws_data_manager, 
            regions=self.data_provider.ec2_regions, 
            manage_ec2=AwsEC2Manager(), 
            object_list_formatter=self.object_list_formatter,
            mode=mode,  # Either 'terminate' or 'cleanup'
            parent=self
        )
        dialog.exec_()

    def object_list_formatter(self, instance_details, object_type):
        if object_type == "ec2_instances":
            formatted_data = {}
            for instance_id, region in instance_details:
                if region not in formatted_data:
                    formatted_data[region] = []
                formatted_data[region].append({"InstanceId": instance_id})
            return formatted_data
        else:
            raise ValueError(f"Unsupported object type: {object_type}")

    def toggle_render_group_filter(self):
        current_text = self.render_group_combo_box.currentText()

        if current_text == "Show All":
            self.data_provider.setRenderGroupFilter('all')
        elif current_text == "Show with RenderGroup":
            self.data_provider.setRenderGroupFilter('withRenderGroup')
        elif current_text == "Show without RenderGroup":
            self.data_provider.setRenderGroupFilter('withoutRenderGroup')

        self.browser.page().runJavaScript("window.fetchData();")

    def launch_parquet_writer(self):
        # Path to the script to be executed
        script_path = os.path.join(os.path.dirname(__file__), 'ec2_instance_parquet_writer.py')

        try:
            if platform.system() == 'Windows':
                # Windows: Use PowerShell to open a new console window and run the script
                command = f'pwsh -Command "& \'{script_path}\'"'  # No -NoExit flag, so it will close automatically
                process = subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif platform.system() == 'Darwin':
                # macOS: Use AppleScript to open a new Terminal window and run the script
                command = f'osascript -e \'tell application "Terminal" to do script "python3 \'{script_path}\'"\''
                process = subprocess.Popen(command, shell=True)
            elif platform.system() == 'Linux':
                # Linux: Use gnome-terminal to open a new terminal window, run the script, then close the terminal
                command = f'gnome-terminal -- bash -c "python3 \'{script_path}\'; exec bash"'
                process = subprocess.Popen(command, shell=True)
            else:
                raise OSError("Unsupported operating system")

            self.subprocesses.append(process)  # Track the subprocess

        except Exception as e:
            print(f"Failed to launch the EC2 Writer: {e}")

    def load_html(self):
        env = Environment(loader=FileSystemLoader('src/aufs/user_tools/packaging/templates'))
        template = env.get_template('ag_grid_data_manager_view.html')
        html_content = template.render()
        self.browser.setHtml(html_content, QUrl("qrc:/"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    directory = None
    if len(sys.argv) > 1:
        directory = sys.argv[1]

    main_window = MainWindow(directory)
    main_window.show()
    sys.exit(app.exec())
