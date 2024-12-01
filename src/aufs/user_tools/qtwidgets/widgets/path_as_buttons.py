# Assume this is in lib/qtwidgets/widgets/path_as_buttons.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton

class DirectorySelector(QWidget):
    def __init__(self, input_path, start_index=0, amount=0, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        
        # Parse the path into components
        path_components = input_path.replace('\\', '/').split('/')
        if amount > 0:
            # If amount is specified, select a range of components
            path_components = path_components[start_index:start_index + amount]
        else:
            # If amount is 0, start_index is the beginning index to slice from
            path_components = path_components[start_index:]
        
        self.path_components = path_components
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)
        for component in self.path_components:
            button = QPushButton(component, self)
            button.clicked.connect(lambda checked, comp=component: self.on_select(comp))
            layout.addWidget(button)
        
        self.setLayout(layout)
        self.setWindowTitle('Select Output Directory')
        self.show()
    
    def on_select(self, component):
        if self.callback:
            self.callback(component)
        self.close()

# # A function to run the DirectorySelector, not needed if you integrate into an existing QApplication
# def get_user_selected_path(input_path, start_index, amount, callback):
#     app = QApplication(sys.argv)
#     ex = DirectorySelector(input_path, start_index, amount, callback)
#     app.exec_()  # This will block until the window is closed

# # Example usage
# if __name__ == "__main__":
#     def user_selected_path(selected_parent):
#         print(f"User selected parent directory: {selected_parent}")
#         # Here you can continue processing with the selected directory

#     # Start the GUI for directory selection
#     input_path_example = 'G:/jobs/IO/IN/client/primary_vfx/THRG2/20231222_rnd_MM/orig_plates/THRG_201_062_0030_rnd/4448x3096/THRG_201_062_0030_rnd.%04d.exr'
#     get_user_selected_path(input_path_example, 2, 3, user_selected_path)
