import sys
import os
import time
import argparse
import pandas as pd
from datetime import datetime, timezone
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog,
    QDialog, QTableWidget, QTableWidgetItem, QCheckBox, QListWidget, QMessageBox, QComboBox, QLabel
)
from PySide6.QtCore import Qt

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.fs_meta.fs_info_from_paths import file_details_df_from_path
from src.aufs.user_tools.deep_editor import DeepEditor


class DirectoryLoaderUI(QMainWindow):
    def __init__(self, jobs_dir=None, client=None, project=None):
        super().__init__()
        self.setWindowTitle("Directory Loader with Scraper")
        self.setGeometry(300, 100, 800, 600)

        # Initialize paths and variables
        self.jobs_dir = jobs_dir or os.path.expanduser("~/.aufs/config/jobs/active")
        self.client = client
        self.project = project
        self.timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.directories = []  # Current directories
        self.initial_directories = []  # Tracks initial state
        self.time_ago_mode = True  # Show relative time by default

        # Setup UI
        self.setup_ui()

        # Load initial clients
        self.load_clients()

        # Select client and project if provided
        if self.client:
            self.set_client(self.client)
        if self.project:
            self.set_project(self.project)

    def setup_ui(self):
        """Setup the UI layout and components."""
        main_layout = QVBoxLayout()
        job_selection_layout = QHBoxLayout()

        # Client selection
        client_selection_layout = QHBoxLayout()
        client_label = QLabel("Select Client:")
        client_selection_layout.addWidget(client_label)
        self.client_dropdown = QComboBox()
        self.client_dropdown.currentIndexChanged.connect(self.update_projects)
        client_selection_layout.addWidget(self.client_dropdown)
        job_selection_layout.addLayout(client_selection_layout)

        # Project selection
        project_selection_layout = QHBoxLayout()
        project_label = QLabel("Select Project:")
        project_selection_layout.addWidget(project_label)
        self.project_dropdown = QComboBox()
        self.project_dropdown.currentIndexChanged.connect(self.load_path_list_files)
        project_selection_layout.addWidget(self.project_dropdown)
        job_selection_layout.addLayout(project_selection_layout)

        main_layout.addLayout(job_selection_layout)

        # Table for displaying directories and "Last Scraped"
        self.directory_table = QTableWidget()
        self.directory_table.setColumnCount(2)
        self.directory_table.setHorizontalHeaderLabels(["Directory Path", "Last Scraped"])
        self.directory_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.directory_table.setSelectionMode(QTableWidget.MultiSelection)
        self.directory_table.itemSelectionChanged.connect(self.update_selected_paths)
        main_layout.addWidget(self.directory_table)

        # Time toggle checkbox
        self.time_toggle_checkbox = QCheckBox("Show Relative Time")
        self.time_toggle_checkbox.setChecked(True)
        self.time_toggle_checkbox.stateChanged.connect(self.toggle_time_display)
        # main_layout.addWidget(self.time_toggle_checkbox)

        # Directory browser button
        browse_directories_button = QPushButton("Browse Directories")
        browse_directories_button.clicked.connect(self.open_directory_browser)
        main_layout.addWidget(browse_directories_button)
                
        # Lower pane for selected directories
        self.directory_list_view = QListWidget()
        self.directory_list_view.setSelectionMode(QListWidget.MultiSelection)
        main_layout.addWidget(self.directory_list_view)

        # Run scraper button
        run_scraper_button = QPushButton("Run Scraper")
        run_scraper_button.clicked.connect(self.run_scraper)
        main_layout.addWidget(run_scraper_button)

        # Bottom control buttons
        button_layout = QHBoxLayout()

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected_directories)
        button_layout.addWidget(remove_button)

        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.clear_all_directories)
        button_layout.addWidget(clear_button)

        self.cancel_button = QPushButton("Cancel Operation")
        self.cancel_button.setEnabled(False)  # Initially disabled
        self.cancel_button.clicked.connect(self.request_cancel)
        button_layout.addWidget(self.cancel_button)

        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)

        main_layout.addLayout(button_layout)

        main_layout.addLayout(button_layout)

        # Central widget setup
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def set_client(self, client):
        """Set the client in the dropdown if available."""
        if client in [self.client_dropdown.itemText(i) for i in range(self.client_dropdown.count())]:
            self.client_dropdown.setCurrentText(client)

    def set_project(self, project):
        """Set the project in the dropdown if available."""
        if project in [self.project_dropdown.itemText(i) for i in range(self.project_dropdown.count())]:
            self.project_dropdown.setCurrentText(project)

    def load_clients(self):
        """Populate the client dropdown based on directories in jobs_dir."""
        if os.path.exists(self.jobs_dir):
            clients = [d for d in os.listdir(self.jobs_dir) if os.path.isdir(os.path.join(self.jobs_dir, d))]
            filtered_clients = [client for client in clients if client not in {"vendors", "OUT", "IN"}]
            self.client_dropdown.addItems(filtered_clients)

    def update_projects(self):
        """Update the project dropdown based on the selected client."""
        client = self.client_dropdown.currentText()
        client_path = os.path.join(self.jobs_dir, client)
        self.project_dropdown.clear()
        if os.path.exists(client_path):
            projects = [d for d in os.listdir(client_path) if os.path.isdir(os.path.join(client_path, d))]
            self.project_dropdown.addItems(projects)

    def load_path_list_files(self):
        """Load directories and scrape times from CSV files into the table."""
        self.directory_table.setRowCount(0)  # Clear the table
        client = self.client_dropdown.currentText()
        project = self.project_dropdown.currentText()
        path_list_dir = os.path.join(self.jobs_dir, client, project, 'fs_updates/path_lists')

        # if not os.path.exists(path_list_dir):
        #     QMessageBox.warning(self, "Path Lists Not Found", f"{path_list_dir} does not exist.")
        #     return

        files = [f for f in os.listdir(path_list_dir) if f.endswith("-path_list.csv")]
        files.sort()

        # Use a dictionary to consolidate paths with the earliest timestamps
        consolidated_data = {}

        for file_name in files:
            csv_path = os.path.join(path_list_dir, file_name)
            scrape_time = self.extract_time_from_filename(file_name)

            try:
                df = pd.read_csv(csv_path)
                for directory in df["Directory Paths"]:
                    # If the path exists, keep the earlier timestamp
                    if directory not in consolidated_data or scrape_time < consolidated_data[directory]:
                        consolidated_data[directory] = scrape_time
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {csv_path}\n{str(e)}")

        # Add consolidated data to the table
        for directory, scrape_time in consolidated_data.items():
            row_position = self.directory_table.rowCount()
            self.directory_table.insertRow(row_position)

            # Add directory path and relative time to the table
            self.directory_table.setItem(row_position, 0, QTableWidgetItem(directory))
            self.directory_table.setItem(row_position, 1, QTableWidgetItem(self.get_relative_time(scrape_time)))

    def update_selected_paths(self):
        """Update the lower pane and selected directories list."""
        self.directory_list_view.clear()
        selected_rows = self.directory_table.selectionModel().selectedRows()

        self.directories = []  # Reset the selected directories
        for row in selected_rows:
            directory = self.directory_table.item(row.row(), 0).text()
            self.directory_list_view.addItem(directory)
            self.directories.append(directory)

    def load_path_list_files(self):
        """Load directories and scrape times from CSV files into the table."""
        self.directory_table.setRowCount(0)  # Clear the table
        client = self.client_dropdown.currentText()
        project = self.project_dropdown.currentText()

        # Ensure client and project are valid
        if not client:
            return
        if not project:
            return

        path_list_dir = os.path.join(self.jobs_dir, client, project, 'fs_updates/path_lists')
        # os.makedirs(path_list_dir, exist_ok=(True))

        # Check if the directory exists
        if not os.path.exists(path_list_dir):
            os.makedirs(path_list_dir, exist_ok=(True))

            # QMessageBox.information(
            #     self,
            #     "Path Lists Not Found",
            #     f"No path list directory exists for the selected project:\n{path_list_dir}",
            # )
            return

        files = [f for f in os.listdir(path_list_dir) if f.endswith("-path_list.csv")]
        files.sort()

        # Use a dictionary to consolidate paths with the latest timestamps
        consolidated_data = {}

        for file_name in files:
            csv_path = os.path.join(path_list_dir, file_name)
            scrape_time = self.extract_time_from_filename(file_name)

            try:
                df = pd.read_csv(csv_path)
                for directory in df["Directory Paths"]:
                    # If the path exists, keep the latest timestamp
                    if directory not in consolidated_data or scrape_time > consolidated_data[directory]:
                        consolidated_data[directory] = scrape_time
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {csv_path}\n{str(e)}")

        # Add consolidated data to the table
        for directory, scrape_time in consolidated_data.items():
            row_position = self.directory_table.rowCount()
            self.directory_table.insertRow(row_position)

            # Add directory path and relative time to the table
            self.directory_table.setItem(row_position, 0, QTableWidgetItem(directory))
            self.directory_table.setItem(row_position, 1, QTableWidgetItem(self.get_relative_time(scrape_time)))

        # Resize columns to fit contents
        self.directory_table.resizeColumnsToContents()

    def open_directory_browser(self):
        """Open directory browser to select multiple directories with an 'Add' button that keeps the dialog open."""
        # Set the initial directory to `self.job_home` or `self.job_files` if available
        initial_dir = self.job_home if hasattr(self, 'job_home') and os.path.exists(self.job_home) else os.getcwd()

        
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setWindowTitle("Select Directories")
        dialog.setDirectory(initial_dir)  # Set the initial directory

        dialog.setLabelText(QFileDialog.Accept, "Add")
        dialog.setLabelText(QFileDialog.Reject, "Close")

        while True:
            if dialog.exec() == QFileDialog.Accepted:
                selected_directories = dialog.selectedFiles()
                self.add_directories_to_list(selected_directories)
            else:
                break

    def add_directories_to_list(self, new_directories):
        """Add new directories to the list view and model."""
        for directory in new_directories:
            if directory not in self.directories:
                self.directories.append(directory)
                self.directory_list_view.addItem(directory)

    def run_scraper(self):
        """Run the file system scraper with the selected directories and settings."""
        client = self.client_dropdown.currentText()
        project = self.project_dropdown.currentText()

        if not self.directories:
            QMessageBox.warning(self, "No Directories Selected", "Please select at least one directory to scrape.")
            return

        shots_csv = os.path.join(self.jobs_dir, client, project, 'shots.csv')
        self.output_name = f"fs_data-{client}_{project}-{self.timestamp}"
        output_csv_file = f"{self.output_name}.csv"
        output_csv = os.path.join(self.jobs_dir, client, project, 'fs_updates', output_csv_file)
        path_list_csv_file = f"{self.output_name}-path_list.csv"
        path_list_csv = os.path.join(self.jobs_dir, client, project, 'fs_updates/path_lists', path_list_csv_file)

        if not os.path.exists(shots_csv):
            QMessageBox.warning(self, "Shots CSV Not Found", f"{shots_csv} not found.")
            return

        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        os.makedirs(os.path.dirname(path_list_csv), exist_ok=True)

        shots_df = pd.read_csv(shots_csv)
        dir_list_df = pd.DataFrame(self.directories, columns=["Directory Paths"])
        print("dir list: ")
        print(dir_list_df)

        # Enable cancelation
        self.cancel_button.setEnabled(True)
        self.cancel_requested = False

        try:
            for i, directory in enumerate(self.directories):
                if self.cancel_requested:
                    QMessageBox.information(self, "Operation Canceled", f"Scraping stopped after {i} directories.")
                    break

                # Scrape details for the current directory
                print("Directory: ", directory)
                df = file_details_df_from_path([directory], client=client, project=project, shots_df=shots_df, output_csv=output_csv)
                if not df.empty:
                    self.open_editor(df)

            if not self.cancel_requested:
                dir_list_df.to_csv(path_list_csv, index=False)
                QMessageBox.information(self, "Scraping Complete", f"Scraped data saved to {path_list_csv}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scrape directories: {str(e)}")
        finally:
            # Disable cancelation
            self.cancel_button.setEnabled(False)
            self.cancel_requested = False

    def extract_time_from_filename(self, filename):
        """Extract the timestamp from the filename and convert it to local time."""
        try:
            # Parse the UTC timestamp from the filename
            timestamp_str = filename.split("-")[2].replace("T", " ").replace("Z", "")
            utc_time = datetime.strptime(timestamp_str, "%Y%m%d %H%M%S").replace(tzinfo=timezone.utc)

            # Convert to local time
            local_time = utc_time.astimezone()
            return local_time
        except (ValueError, IndexError):
            return None  # Return None if timestamp cannot be parsed
            
    def toggle_time_display(self):
        """Toggle between relative time and exact timestamps."""
        self.time_ago_mode = self.time_toggle_checkbox.isChecked()

        for row in range(self.directory_table.rowCount()):
            timestamp_item = self.directory_table.item(row, 1)
            directory_item = self.directory_table.item(row, 0)

            # Ensure items exist
            if not timestamp_item or not directory_item:
                continue

            # Retrieve the stored scrape time
            timestamp_str = directory_item.text()
            timestamp = self.extract_time_from_filename(timestamp_str)

            if not timestamp:
                timestamp_item.setText("Unknown")
                continue

            # Update display based on mode
            if self.time_ago_mode:
                timestamp_item.setText(self.get_relative_time(timestamp))
            else:
                timestamp_item.setText(timestamp.strftime("%Y-%m-%d %H:%M:%S"))

    def get_relative_time(self, timestamp):
        """Convert a timestamp to a relative time string."""
        if not timestamp:
            return "Unknown"

        # Make datetime.now() timezone-aware
        now = datetime.now(timezone.utc).astimezone()  # Convert to local timezone

        delta = now - timestamp
        if delta.days > 0:
            return f"{delta.days} days ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} hours ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} mins ago"
        else:
            return "Just now"
        
    def remove_selected_directories(self):
        """Remove selected directories from the lower pane."""
        selected_items = self.directory_list_view.selectedItems()
        for item in selected_items:
            self.directory_list_view.takeItem(self.directory_list_view.row(item))

    def clear_all_directories(self):
        """Clear all directories from the lower pane."""
        self.directory_list_view.clear()

    def open_editor(self, df):
        """Open the DeepEditor inside a modal dialog."""
        editor_dialog = QDialog(self)
        editor_dialog.setWindowTitle("Edit DataFrame")
        editor_dialog.setModal(True)
        editor_dialog.resize(1000, 800)
        editor = DeepEditor(dataframe_input=df, parent=editor_dialog)
        layout = QVBoxLayout(editor_dialog)
        layout.addWidget(editor)
        editor_dialog.setLayout(layout)
        editor_dialog.exec()

    def request_cancel(self):
        """Set the cancelation flag to True."""
        self.cancel_requested = True
        QMessageBox.information(self, "Cancel Requested", "The current operation will stop shortly.")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Directory Loader with Scraper")
    parser.add_argument("--jobs_dir", type=str, help="Path to the jobs directory")
    parser.add_argument("--client", type=str, help="Client to select on startup")
    parser.add_argument("--project", type=str, help="Project to select on startup")

    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = DirectoryLoaderUI(jobs_dir=args.jobs_dir, client=args.client, project=args.project)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
