import sys
import os
import time
import argparse
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QFileDialog, QListWidget, QMessageBox, QComboBox, QLabel, QDialog, QCheckBox, QTreeWidget, QTreeWidgetItem
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
        self.directories = []

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

        # Load directories from CSV button with checkbox
        get_dirs_list_layout = QHBoxLayout()

        # Directory browser button
        browse_directories_button = QPushButton("Browse Directories")
        browse_directories_button.clicked.connect(self.open_directory_browser)
        get_dirs_list_layout.addWidget(browse_directories_button)

        load_csv_button = QPushButton("Load Directories from CSV")
        load_csv_button.clicked.connect(self.load_directories_from_csv)
        get_dirs_list_layout.addWidget(load_csv_button)

        self.include_first_row_checkbox = QCheckBox("Include First Row")
        self.include_first_row_checkbox.setChecked(False)
        get_dirs_list_layout.addWidget(self.include_first_row_checkbox)

        main_layout.addLayout(get_dirs_list_layout)

        # Tree view to display CSV files in `path_lists`
        self.csv_tree = QTreeWidget()
        self.csv_tree.setHeaderLabel("Saved Directory Lists")
        self.csv_tree.itemClicked.connect(self.load_selected_csv)
        main_layout.addWidget(self.csv_tree)

        # Directory list view
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

        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)

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
            self.client_dropdown.addItems(clients)

    def update_projects(self):
        """Update the project dropdown based on the selected client and refresh path list."""
        client = self.client_dropdown.currentText()
        client_path = os.path.join(self.jobs_dir, client)
        
        self.project_dropdown.clear()
        if os.path.exists(client_path):
            projects = [d for d in os.listdir(client_path) if os.path.isdir(os.path.join(client_path, d))]
            self.project_dropdown.addItems(projects)

    def load_path_list_files(self):
        """Load all CSV files in the path_lists directory into the tree view."""
        self.csv_tree.clear()
        client = self.client_dropdown.currentText()
        project = self.project_dropdown.currentText()
        path_list_dir = os.path.join(self.jobs_dir, client, project, 'fs_updates/path_lists')
        self.job_home = path_list_dir

        if os.path.exists(path_list_dir):
            for file_name in os.listdir(path_list_dir):
                if file_name.endswith(".csv"):
                    file_item = QTreeWidgetItem(self.csv_tree, [file_name])
                    file_item.setData(0, Qt.UserRole, os.path.join(path_list_dir, file_name))

    def load_directories_from_csv(self, csv_path=None):
        """Load directories from a CSV file, optionally including the header row."""
        if not csv_path:
            # Open file dialog if no path is provided
            file_dialog = QFileDialog(self)
            csv_path, _ = file_dialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        
        if csv_path:
            try:
                # Use header=0 if checkbox is checked, else use header=None
                header = None if self.include_first_row_checkbox.isChecked() else 0
                
                # Read directories from CSV into a list and add to directories list
                df = pd.read_csv(csv_path, header=header)
                new_directories = df.iloc[:, 0].tolist()  # Use .iloc to avoid column name issues
                
                # Clear the current list first and add new directories
                self.clear_all_directories()
                self.add_directories_to_list(new_directories)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")

    def load_selected_csv(self, item):
        """Load the directory paths from the selected CSV file in the tree."""
        csv_path = item.data(0, Qt.UserRole)
        self.load_directories_from_csv(csv_path)  # Reuse load_directories_from_csv for loading from tree selection

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

    def remove_selected_directories(self):
        """Remove selected directories from the list."""
        selected_items = self.directory_list_view.selectedItems()
        for item in selected_items:
            self.directories.remove(item.text())
            self.directory_list_view.takeItem(self.directory_list_view.row(item))

    def clear_all_directories(self):
        """Clear all directories from the list."""
        self.directories.clear()
        self.directory_list_view.clear()

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
        # print(shots_df)
        dir_list_df = pd.DataFrame(self.directories, columns=["Directory Paths"])

        try:
            df = file_details_df_from_path(self.directories, client=client, project=project, shots_df=shots_df, output_csv=output_csv)
            if df.empty:
                QMessageBox.information(self, "No Data Found", "No data found in the selected directories.")
                return

            self.open_editor(df)
            dir_list_df.to_csv(path_list_csv, index=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scrape directories: {str(e)}")

    def open_editor(self, df):
        """Open the DeepEditor inside a modal dialog to display and edit the DataFrame."""
        button_flags = {
            'exit': False,
            'save': False,
            'sort_column': False,
            'set_column_type': False,
            'dtype_dropdown': False
        }
        editor_dialog = QDialog(self)
        editor_dialog.setWindowTitle("Edit DataFrame")
        editor_dialog.setModal(True)
        editor_dialog.resize(1000, 800)

        editor = DeepEditor(dataframe_input=df, button_flags=button_flags, parent=editor_dialog)
        layout = QVBoxLayout(editor_dialog)
        layout.addWidget(editor)
        editor_dialog.setLayout(layout)
        editor_dialog.exec()

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