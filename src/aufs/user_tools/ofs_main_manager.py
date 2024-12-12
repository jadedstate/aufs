import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QStackedWidget, 
                               QWidget, QToolBar)
from PySide6.QtGui import QAction

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

# Import the utilities (SnapshotUtility and EnvConfigUtility)
from src.aufs.user_tools.ofs_snapshot_utility import SnapshotUtility
from src.aufs.user_tools.ofs_config_dirs import EnvConfigUtility
from src.aufs.user_tools.ofs_destroy_filesystem import DestroyFilesystemUtility


class MainUtility(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ObjectiveFS Utilities")
        self.setGeometry(100, 100, 1200, 800)

        # Create a toolbar
        self.toolbar = QToolBar("Utility Toolbar")
        self.addToolBar(self.toolbar)

        # Create actions for the toolbar buttons
        env_config_action = QAction("Env Config Utility", self)
        snapshot_action = QAction("Snapshot Utility", self)
        destroy_action = QAction("Destroy FS Utility", self)

        # Add actions to the toolbar
        self.toolbar.addAction(snapshot_action)
        self.toolbar.addAction(env_config_action)
        self.toolbar.addAction(destroy_action)

        # Create a stacked widget to switch between utilities
        self.stacked_widget = QStackedWidget(self)

        # Instantiate the utilities and add them to the stacked widget
        self.snapshot_utility = SnapshotUtility()
        self.env_config_utility = EnvConfigUtility()
        self.destroy_fs_utility = DestroyFilesystemUtility()

        # Add the utilities to the stacked widget
        self.stacked_widget.addWidget(self.env_config_utility)
        self.stacked_widget.addWidget(self.snapshot_utility)
        self.stacked_widget.addWidget(self.destroy_fs_utility)

        # Connect the toolbar actions to switch views in the stacked widget
        snapshot_action.triggered.connect(lambda: self.stacked_widget.setCurrentWidget(self.snapshot_utility))
        env_config_action.triggered.connect(lambda: self.stacked_widget.setCurrentWidget(self.env_config_utility))
        destroy_action.triggered.connect(lambda: self.stacked_widget.setCurrentWidget(self.destroy_fs_utility))

        # Set up the layout for the main window
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stacked_widget)

        # Create a container widget for the main layout
        container_widget = QWidget()
        container_widget.setLayout(main_layout)

        # Set the container widget as the central widget of the main window
        self.setCentralWidget(container_widget)


if __name__ == "__main__":
    # Initialize the application
    app = QApplication(sys.argv)

    # Create and show the MainUtility window
    window = MainUtility()
    window.show()

    # Run the application's event loop
    sys.exit(app.exec())
