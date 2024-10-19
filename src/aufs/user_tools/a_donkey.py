from PySide6.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QFileDialog
import sys
import os

from config_controller import MainWidgetWindow  # Assuming MainWidgetWindow is in 'config_controller.py'

class MainApp(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        self.setWindowTitle("Production App Wrapper")
        self.setGeometry(100, 100, 1000, 800)

        # Create the central widget and its layout
        central_widget = QWidget()
        self.central_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Top buttons layout
        button_layout = QHBoxLayout()

        # Dummy buttons (as placeholders)
        dummy_button1 = QPushButton("Dummy Button 1")
        dummy_button2 = QPushButton("Dummy Button 2")
        button_layout.addWidget(dummy_button1)
        button_layout.addWidget(dummy_button2)

        # Load button to choose the directory
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_directory)  # Connect to load_directory method
        button_layout.addWidget(load_button)

        # Add the button layout to the main layout
        self.central_layout.addLayout(button_layout)

        # Initialize the MainWidgetWindow
        self.main_widget = None

        # Initial config path if provided
        if config_path:
            self.load_main_widget(config_path)

    def load_directory(self):
        """Open a file dialog to select the config directory."""
        config_dir = QFileDialog.getExistingDirectory(self, "Select Config Directory")

        if config_dir:
            print(f"Selected directory: {config_dir}")
            self.load_main_widget(config_dir)

    def load_main_widget(self, config_path):
        """Load or update the MainWidgetWindow with the selected config path."""
        # If the main widget already exists, just update its root path
        if self.main_widget:
            self.main_widget.update_root_path(config_path)  # Update existing widget
        else:
            # Otherwise, create the main widget and add it to the layout
            self.main_widget = MainWidgetWindow(config_path)
            self.central_layout.addWidget(self.main_widget)  # Add it to the layout

# Simulate how the module will be used in production
def run_app(config_path=None):
    app = QApplication(sys.argv)

    main_app_window = MainApp(config_path)

    # Show the window
    main_app_window.show()

    # Run the application loop
    sys.exit(app.exec())

# Entry point for the application
if __name__ == "__main__":
    # Optionally hardcode the directory or leave it empty to prompt for selection
    config_dir = os.path.expanduser("~/Downloads/aufs_packaging/my_configs/boo")

    # Call the function that runs the application (use None to prompt user)
    run_app(config_dir)  # Or run_app(None) to prompt user
