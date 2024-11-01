import pandas as pd
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
import pyarrow.parquet as pq
from parquet_metadata_editor import MetadataObjectsList

# Load metadata from the Parquet file
def load_metadata_from_parquet(parquet_file_path):
    """
    Load metadata from a Parquet file and return a dictionary of metadata containers.
    This includes file-level, column-level, and row-group-level metadata.
    """
    parquet_file = pq.ParquetFile(parquet_file_path)
    metadata_containers = {}

    # --- File-level metadata ---
    file_metadata = parquet_file.metadata.metadata
    if file_metadata:
        metadata_containers["File"] = pd.DataFrame(
            [(k.decode('utf-8'), v.decode('utf-8') if isinstance(v, bytes) else v) for k, v in file_metadata.items()],
            columns=['Key', 'Value']
        )

    # --- Column-level metadata ---
    for i, field in enumerate(parquet_file.schema_arrow):
        column_metadata = field.metadata
        if column_metadata:
            metadata_containers[f"Column:{i}"] = pd.DataFrame(
                [(k.decode('utf-8'), v.decode('utf-8') if isinstance(v, bytes) else v) for k, v in column_metadata.items()],
                columns=['Key', 'Value']
            )

    # --- Row-group-level metadata ---
    for rg_index in range(parquet_file.metadata.num_row_groups):
        row_group = parquet_file.metadata.row_group(rg_index)
        row_group_metadata = row_group.to_dict()
        metadata_containers[f"RowGroup:{rg_index}"] = pd.DataFrame(
            [(k, v) for k, v in row_group_metadata.items()],
            columns=['Key', 'Value']
        )

    return metadata_containers

# Function to select which metadata container the user wants to edit
def select_metadata_container(metadata_containers):
    """
    Display a dialog for the user to select which metadata container to edit.
    """
    container_options = list(metadata_containers.keys())
    item, ok = QInputDialog.getItem(
        None, "Select Metadata Container", 
        "Choose the metadata container to edit:", container_options, 0, False
    )

    if ok and item:
        return item
    else:
        QMessageBox.warning(None, "No Selection", "No metadata container was selected.")
        return None

# Main function to load metadata and allow the user to edit a selected container
def main(parquet_file_path):
    app = QApplication([])

    # Step 1: Load all metadata containers from the Parquet file
    metadata_containers = load_metadata_from_parquet(parquet_file_path)

    # Step 2: Let the user select which metadata container to edit
    selected_container_key = select_metadata_container(metadata_containers)

    if not selected_container_key:
        return  # If no selection was made, exit the app

    # Step 3: Pass the selected metadata container (as DataFrame) to the editor
    metadata_df = metadata_containers[selected_container_key]
    editor_window = MetadataObjectsList(metadata_df=metadata_df)
    editor_window.show()

    # Run the application (this will block until the UI is closed)
    app.exec()

    # Step 4: After the editor closes, get the modified DataFrame
    modified_metadata_df = editor_window.get_modified_metadata()

    # Step 5: Here you would save the modified DataFrame (back to Parquet, JSON, etc.)
    print("Modified Metadata for:", selected_container_key)
    print(modified_metadata_df)

if __name__ == '__main__':
    parquet_file = "/Users/uel/Dasein/daseinVfxPipe/pipeline/GitHub/steve-smb-002.parquet"
    main(parquet_file)
