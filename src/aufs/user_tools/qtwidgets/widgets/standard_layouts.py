# standard_layouts.py

from PyQt5.QtWidgets import QHBoxLayout
from .custom_buttons import CustomCancelButton, CustomOKButton

class twoBtnBox:
    @staticmethod
    def ok_cancel_ref(parent=None):
        hbox = QHBoxLayout()
        cancel_button = CustomCancelButton(parent)
        ok_button = CustomOKButton(parent)
        hbox.addWidget(ok_button)
        hbox.addWidget(cancel_button)
        # Return both the layout and button references
        return hbox, cancel_button, ok_button

    @staticmethod
    def ok_cancel_param(cancel_text="Cancel", ok_text="OK", parent=None):
        hbox = QHBoxLayout()
        cancel_button = CustomCancelButton(parent)
        cancel_button.setText(cancel_text)  # Set text from parameter
        ok_button = CustomOKButton(parent)
        ok_button.setText(ok_text)  # Set text from parameter
        hbox.addWidget(ok_button)
        hbox.addWidget(cancel_button)
        return hbox

    @staticmethod
    def cancel_ok_ref(parent=None):
        hbox = QHBoxLayout()
        cancel_button = CustomCancelButton(parent)
        ok_button = CustomOKButton(parent)
        hbox.addWidget(cancel_button)
        hbox.addWidget(ok_button)
        # Return both the layout and button references
        return hbox, cancel_button, ok_button

    @staticmethod
    def cancel_ok_ref_param(cancel_text="Cancel", ok_text="OK", parent=None):
        hbox = QHBoxLayout()
        cancel_button = CustomCancelButton(parent)
        cancel_button.setText(cancel_text)  # Set text from parameter
        ok_button = CustomOKButton(parent)
        ok_button.setText(ok_text)  # Set text from parameter
        hbox.addWidget(cancel_button)
        hbox.addWidget(ok_button)
        return hbox
