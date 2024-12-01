import sys
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QDialog, QApplication
from PySide6.QtCore import Qt

class ConfirmationDialog(QDialog):
    def __init__(self, action_desc, formatted_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Action")
        self.init_ui(action_desc, formatted_data)

    def init_ui(self, action_desc, formatted_data):
        layout = QVBoxLayout(self)

        total_instances = sum(len(instances) for instances in formatted_data.values())
        total_regions = len(formatted_data)
        action_label = QLabel(f"You are about to perform the following command: {action_desc} "
                              f"on {total_instances} instances in {total_regions} regions.")
        action_label.setWordWrap(True)
        layout.addWidget(action_label)

        for region in sorted(formatted_data.keys()):
            region_label = QLabel(f"Region: {region}")
            region_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(region_label)

            # Format instance IDs into lines with 3 IDs per line
            instances = formatted_data[region]
            instance_lines = []
            for i in range(0, len(instances), 3):
                line = ", ".join(instance["InstanceId"] for instance in instances[i:i+3])
                instance_lines.append(line)
            
            instance_text = QTextEdit("\n".join(instance_lines))
            instance_text.setReadOnly(True)
            instance_text.setFixedHeight(20 * min(len(instance_lines), 7))  # 20 pixels per line, max 7 lines
            layout.addWidget(instance_text)

        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        proceed_button = QPushButton("Proceed")
        proceed_button.clicked.connect(self.accept)
        button_layout.addWidget(proceed_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setMinimumWidth(400)
        self.setWindowModality(Qt.ApplicationModal)

    def get_confirmation(self):
        return self.exec_() == QDialog.Accepted

def run_confirmation_dialog(action_desc, formatted_data):
    # Ensure there is a QApplication instance
    app = QApplication.instance() or QApplication(sys.argv)
    
    dialog = ConfirmationDialog(action_desc, formatted_data)
    result = dialog.get_confirmation()

    if not QApplication.instance():
        app.quit()

    return result
