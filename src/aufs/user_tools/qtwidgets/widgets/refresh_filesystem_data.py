# lib/qtwidgets/widgets/refresh_filesystem_data.py
import datetime as datetime
import pandas as pd
from pandas import DataFrame, concat
import os
import shutil
import filelock

from googleGetShotData import GoogleSheetShotData
from search_for_files_standard import FileSearcher
from search_for_links_standard import LinkSearcher
from sequence_finder import SequenceFinder
from add_shot_names import add_shot_names_to_results

class FileDataProcessor:
    def __init__(self, job_setup_data, file_path=None, output_file=None):
        self.dataframe = None
        self.job_setup_data = job_setup_data
        self.file_path = file_path 
        # Extract 'client', 'project', and 'job' from job_setup_data
        self.client = self.job_setup_data.get('CLIENT') if self.job_setup_data else None
        self.project = self.job_setup_data.get('PROJECT') if self.job_setup_data else None
        self.job = f"{self.client}-{self.project}" if self.client and self.project else None
        # self.output_file = output_file 

    def read_ods_file(self, file_path=None, sheet_name=None):
        """
        Reads an ODS file and loads it into a pandas DataFrame.
        If a sheet name is provided, it reads that specific sheet.
        If no sheet name is provided, it defaults to reading the first sheet.
        """
        # Use default output file if no file_path is provided
        file_path = file_path or self.output_file

        try:
            if sheet_name is None:
                # Load only the first sheet as a DataFrame if no sheet name is provided
                self.dataframe = pd.read_excel(file_path, engine='odf', sheet_name=0)
            else:
                # Load the specified sheet as a DataFrame
                self.dataframe = pd.read_excel(file_path, engine='odf', sheet_name=sheet_name)
            
            print(f"Data from {file_path} loaded successfully.")
        except Exception as e:
            print(f"Error reading ODS file: {e}")
            self.dataframe = None

    def filter_data_by_fields(self, header, values):
        """
        Filters the DataFrame for rows where the column 'header' matches any of the 'values'.

        Args:
            header (str): The column header to match against.
            values (list): A list of values to filter the rows by.

        Returns:
            A pandas DataFrame with the filtered data.
        """
        if self.dataframe is not None:
            if header in self.dataframe.columns:
                filtered_df = self.dataframe[self.dataframe[header].isin(values)]
                return filtered_df
            else:
                print(f"Header '{header}' not found in data.")
                return None
        else:
            print("Data not loaded. Please read in data before filtering.")
            return None

    def handle_action(self, action_type, **kwargs):
        """
        Handles different actions for processing data.

        Args:
            action_type (str): The type of action to perform.
            **kwargs: Additional keyword arguments required for processing.

        Returns:
            A pandas DataFrame with the processed data based on action type.
        """
        if action_type == 'get_sequences_for_rv':
            return self.get_sequences_for_rv(**kwargs)
        # Other elif clauses for different actions can be added here.
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def get_sequences_for_rv(self, shot_name):
        """
        Filters the DataFrame for the 'SEQUENCE' column based on a 'SHOTNAME'.
        Ensures data is loaded before filtering.
        """
        print(f"SHOT WE'RE LOOKING FOR: {shot_name}")
        # Ensure the DataFrame is loaded and is a DataFrame
        if self.dataframe is None or not isinstance(self.dataframe, pd.DataFrame):
            print("Dataframe not loaded or is not a DataFrame, attempting to load...")
            self.read_ods_file()  # This will load the first sheet by default

        # Ensure the DataFrame has the necessary columns
        if 'SEQUENCE' in self.dataframe.columns and 'SHOTNAME' in self.dataframe.columns:
            # Filter sequences by shot name and exclude NaN values
            filtered_sequences = self.dataframe[self.dataframe['SHOTNAME'] == shot_name]['SEQUENCE'].dropna()
            
            # Get unique sequences
            unique_sequences = filtered_sequences.unique()
            
            # Debug print to check the filtered and unique sequences
            print(f"Filtered unique sequences for {shot_name}: {unique_sequences}")
            
            return list(unique_sequences)  # Convert to list for consistent output format
        else:
            print("Data loaded but 'SEQUENCE'/'SHOTNAME' column not found.")
            return []

    def get_shot_seqs_with_first_last(self, shot_name):
        """
        Filters the DataFrame for the 'SEQUENCE', 'FIRSTFRAME', and 'LASTFRAME' columns based on a 'SHOTNAME'.
        Ensures data is loaded before filtering and returns a list of dictionaries with sequence and frame range details,
        ensuring each sequence is unique.
        """
        print(f"SHOT WE'RE LOOKING FOR: {shot_name}")
        # Ensure the DataFrame is loaded and is a DataFrame
        if self.dataframe is None or not isinstance(self.dataframe, pd.DataFrame):
            print("Dataframe not loaded or is not a DataFrame, attempting to load...")
            self.read_ods_file()  # This will load the first sheet by default

        required_columns = ['SEQUENCE', 'SHOTNAME', 'FIRSTFRAME', 'LASTFRAME']
        # Ensure the DataFrame has the necessary columns
        if all(column in self.dataframe.columns for column in required_columns):
            # Filter DataFrame by shot name and exclude rows with NaN in any of the required columns
            filtered_df = self.dataframe[self.dataframe['SHOTNAME'] == shot_name].dropna(subset=required_columns)

            # Extract relevant data into a set of tuples to remove duplicates
            sequences_with_frames_set = {(
                row['SEQUENCE'],
                int(row['FIRSTFRAME']),
                int(row['LASTFRAME'])
            ) for index, row in filtered_df.iterrows()}

            # Convert the set back to a list of dictionaries
            sequences_with_frames = [{'SEQUENCE': seq, 'FIRSTFRAME': first, 'LASTFRAME': last}
                                    for seq, first, last in sequences_with_frames_set]

            # Debug print to check the filtered sequences with their frame ranges
            print(f"Filtered sequences with frame range for {shot_name}: {sequences_with_frames}")

            return sequences_with_frames
        else:
            print(f"Data loaded but one or more of the required columns {required_columns} not found.")
            return []

    def refresh_data_for_all_paths(self, refresh_type, workpaths):
        """
        Refreshes files or links data for all specified work paths.

        Args:
            refresh_type (str): The type of refresh to perform ('links' or 'files').
            workpaths (list): A list of paths to refresh data for.
        """
        for path in workpaths:
            print(f"Refreshing {refresh_type} data for path: {path}")
            if refresh_type == 'links':
                self.update_fs_links_data(specific_path=path)
            elif refresh_type == 'files':
                self.update_fs_files_data(specific_path=path)
            else:
                print(f"Unknown refresh type: {refresh_type}")

    def refresh_all_data_for_path(self, specific_path):
        """
        Refreshes both links and files data for a specific path.
        """
        print(f"Refreshing all data for path: {specific_path}")
        self.update_fs_links_data(specific_path)
        self.update_fs_files_data(specific_path)

    def update_fs_files_data(self, specific_path=None):
        update_path = specific_path if specific_path else self.file_path

        # Retrieve shot data and search sequences
        google_sheet_shot_data = GoogleSheetShotData(self.job_setup_data)
        shot_data_df = google_sheet_shot_data.get_shot_data_df()
        file_searcher = FileSearcher(update_path)
        files_df = file_searcher.run()
        column_name = 'FILE'
        image_seq_exts = ['tif', 'tiff', 'dpx', 'exr', 'jpg', 'jpeg', 'png']
        sequence_finder = SequenceFinder(files_df, column_name, image_seq_exts)
        sequence_df = sequence_finder.get_sequences()
        # print(f"SEQUENCE_DF from seq finder: {sequence_df}")
        final_df = add_shot_names_to_results(shot_data_df, sequence_df)
        # print(f"FINAL after ADD_SHOTNAMES: {final_df}")

        # Define file path for the specific path
        safe_specific_path = specific_path.replace(":", "").replace("\\", "_").replace("/", "_").replace(" ", "_")
        output_file_path = os.path.join("F:\\", "jobs", "IO", "work", "tracking", f"{self.client}-{self.project}", f"FILES_{safe_specific_path}.ods")
        backup_dir = os.path.join(os.path.dirname(output_file_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)

        lock = filelock.FileLock(f"{output_file_path}.lock")

        with lock:
            # Backup existing file
            if os.path.exists(output_file_path):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_path = os.path.join(backup_dir, f"{timestamp}-{os.path.basename(output_file_path)}")
                shutil.copy(output_file_path, backup_path)

            # Ensure the document exists, or create a new one
            if not os.path.exists(output_file_path):
                # Create an empty DataFrame
                empty_df = pd.DataFrame()
                # Save the empty DataFrame as an ODS file, this will create a file with the default sheet named 'Sheet1'
                empty_df.to_excel(output_file_path, engine='odf', index=False)
                # print(f"New ODS file created at {output_file_path}")

            # Load the existing data from the sheet, if any
            # Check if file is not empty before appending
            if os.path.getsize(output_file_path) > 0:
                existing_df = pd.read_excel(output_file_path, engine='odf', sheet_name=0)  # Assuming first sheet
                appended_df = pd.concat([existing_df, final_df])
                appended_df.to_excel(output_file_path, engine='odf', index=False)
                # print(f"Data updated and written to {output_file_path}")

                # Deduplicate the ODS file after appending new data
                self.deduplicate_ods_file(output_file_path)
            else:
                # If the file is empty, directly use final_df as appended_df
                final_df.to_excel(output_file_path, engine='odf', index=False)
                print(f"Data written to {output_file_path}")

    def update_fs_links_data(self, specific_path=None):
        update_path = specific_path if specific_path else self.file_path

        # Retrieve shot data and search sequences
        google_sheet_shot_data = GoogleSheetShotData(self.job_setup_data)
        shot_data_df = google_sheet_shot_data.get_shot_data_df()
        link_searcher = LinkSearcher(update_path)
        links_df = link_searcher.run()
        # print(f"LINKS DF: {links_df}")
        column_name = 'LINK'
        image_seq_exts = ['tif', 'tiff', 'dpx', 'exr', 'jpg', 'jpeg', 'png']  # Add or remove extensions as needed
        sequence_finder = SequenceFinder(links_df, column_name, image_seq_exts)
        sequence_df = sequence_finder.get_sequences()
        # print(f"SEQ DF: {sequence_df}")
        final_df = add_shot_names_to_results(shot_data_df, sequence_df)
        #print(f"FINAL after ADD_SHOTNAMES: {final_df}")

        # Define file path for the specific path
        safe_specific_path = specific_path.replace(":", "").replace("\\", "_").replace("/", "_")
        output_file_path = os.path.join("F:\\", "jobs", "IO", "work", "tracking", f"{self.client}-{self.project}", f"LINKS_{safe_specific_path}.ods")
        backup_dir = os.path.join(os.path.dirname(output_file_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)

        lock = filelock.FileLock(f"{output_file_path}.lock")

        with lock:
            # Backup existing file
            if os.path.exists(output_file_path):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_path = os.path.join(backup_dir, f"{timestamp}-{os.path.basename(output_file_path)}")
                shutil.copy(output_file_path, backup_path)

            # Ensure the document exists, or create a new one
            if not os.path.exists(output_file_path):
                # Create an empty DataFrame
                empty_df = pd.DataFrame()
                # Save the empty DataFrame as an ODS file, this will create a file with the default sheet named 'Sheet1'
                empty_df.to_excel(output_file_path, engine='odf', index=False)
                print(f"New ODS file created at {output_file_path}")

            # Load the existing data from the sheet, if any
            # Check if file is not empty before appending
            if os.path.getsize(output_file_path) > 0:
                existing_df = pd.read_excel(output_file_path, engine='odf', sheet_name=0)  # Assuming first sheet
                appended_df = pd.concat([existing_df, final_df])
                appended_df.to_excel(output_file_path, engine='odf', index=False)
                print(f"Data updated and written to {output_file_path}")

                # Deduplicate the ODS file after appending new data
                self.deduplicate_ods_file(output_file_path)
            else:
                # If the file is empty, directly use final_df as appended_df
                final_df.to_excel(output_file_path, engine='odf', index=False)
                print(f"Data written to {output_file_path}")

    def deduplicate_ods_file(self, file_path):
        """
        Reads an ODS file, deduplicates its data, rearranges columns to match a template,
        and writes the cleaned data back to the file.

        Args:
            file_path (str): Path to the ODS file to be processed.
        """
        try:
            # Load the data from the ODS file
            df = pd.read_excel(file_path, engine='odf', sheet_name=0)  # Assuming the data is in the first sheet

            # Normalize paths in all string columns to use Linux standard (forward slashes)
            for column in df.select_dtypes(include=['object']).columns:
                df[column] = df[column].apply(lambda x: x.replace('\\', '/') if isinstance(x, str) else x)

            # Deduplicate the data
            deduplicated_df = df.drop_duplicates(keep='first')

            # Rearrange columns in the deduplicated DataFrame to follow the template
            self.dataframe = deduplicated_df  # Temporarily set deduplicated_df as the object's dataframe
            self.rearrange_columns_to_template()  # No argument needed if using the method's default template
            rearranged_df = self.dataframe  # Retrieve the rearranged dataframe

            # Write the rearranged and deduplicated data back to the ODS file
            rearranged_df.to_excel(file_path, engine='odf', index=False)
            print(f"Deduplicated and rearranged data written to {file_path}")
        except Exception as e:
            print(f"Error processing ODS file: {e}")

    def rearrange_columns_to_template(self, template=None):
        """
        Rearranges columns in the dataframe to match the specified template,
        with any remaining columns appended at the end in their original order.

        Args:
            template (list, optional): List of column names in the desired order.
                                       Defaults to a predefined template.
        """
        # Define the default template if none is provided
        if template is None:
            template = [
                'SHOTNAME', 'SEQUENCE', 'FIRSTFRAME', 'LASTFRAME', 'MISSINGFRAMES',
                'NUMBERPADDING', 'SEQUENCEFILENAME', 'TOTALSIZE', 'FILE', 'LINK',
                'TARGET', 'FILESIZE', 'CREATION_TIME', 'MODIFICATION_TIME', 'DOTEXTENSION'
            ]

        # Ensure the dataframe is loaded
        if self.dataframe is not None:
            # Identify columns in the dataframe that are not in the template
            extra_cols = [col for col in self.dataframe.columns if col not in template]
            
            # Rearrange columns to match the template first, then append any extra columns in their original order
            new_order = template + extra_cols
            
            # Reorder the dataframe columns based on the new order, ensuring only existing columns are included
            self.dataframe = self.dataframe[[col for col in new_order if col in self.dataframe.columns]]
        else:
            print("Dataframe not loaded. Please read in data before rearranging columns.")
