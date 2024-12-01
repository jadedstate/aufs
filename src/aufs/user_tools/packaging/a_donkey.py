import os
import sys
import pandas as pd
from PySide6.QtWidgets import QApplication

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.data_provisioning_widget import DataProvisioningWidget

# File paths for testing
csv_file = "/Users/uel/.aufs/config/jobs/active/vendors/amolesh/rr_mumbai/sessions/comp/comp-20241125113138.csv"
root_path = "/Users/uel/.aufs/config/jobs/IN/rr_mumbai/amolesh"

def main():
    # Ensure the CSV file exists
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        return

    # Read the CSV into a DataFrame
    try:
        dtype_mapping = {
            'PADDING': str,
            'FIRSTFRAME': str,
            'LASTFRAME': str,
        }
        df = pd.read_csv(csv_file, dtype=dtype_mapping)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Initialize the QApplication
    app = QApplication(sys.argv)

    # Create the DataProvisioningWidget
    widget = DataProvisioningWidget(input_df=df, root_package_path=root_path)

    # Show the widget
    widget.setWindowTitle("Data Provisioning Widget - Test")
    widget.show()

    # Execute the app
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
