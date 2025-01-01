from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.fs_meta.ingest_job_data import MainAppWidget, SessionManager

class PopupDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Popup with Embedded App")
        self.resize(1100, 800)

        # Create SessionManager
        session_manager = SessionManager("~/.aufs/config/jobs/active")

        # Embed the MainAppWidget
        self.main_widget = MainAppWidget(session_manager=session_manager, parent=self)

        # Add to Layout
        layout = QVBoxLayout()
        layout.addWidget(self.main_widget)

        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PopupDialog()
    dialog.exec()  # Popup as a dialog
