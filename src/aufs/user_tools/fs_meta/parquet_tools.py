import pandas as pd
from datetime import datetime
import os
import re
import pyarrow.parquet as pq
import pyarrow as pa
from .files_paths import Singleton

class ParquetFileWithSingleton:
    def __init__(self, file_path, lock_identifier=None):
        self.file_path = file_path
        self.lock_identifier = lock_identifier if lock_identifier else os.path.basename(file_path)
        self.lock = Singleton(self.lock_identifier)

    def read_parquet_file_or_create_standard_scraper_dataframe2(self):
        if self.lock.acquire_lock():
            try:
                if os.path.exists(self.file_path):
                    return pd.read_parquet(self.file_path)
                else:
                    return pd.DataFrame(columns=["FILE", "FILESIZE", "CREATION_TIME", "MODIFICATION_TIME", "ISLINK", "TARGET"])
            finally:
                self.lock.release_lock()
        else:
            print(f"Could not acquire lock for {self.file_path}")

    def read_parquet_file2(self):
        if self.lock.acquire_lock():
            try:
                if os.path.exists(self.file_path):
                    return pd.read_parquet(self.file_path)
                else:
                    print(f"No file @ {self.file_path}")
            finally:
                self.lock.release_lock()
        else:
            print(f"Could not acquire lock for {self.file_path}")

    def write_parquet_file2(self, df):
        if self.lock.acquire_lock():
            try:
                df.to_parquet(self.file_path, index=False)
            finally:
                self.lock.release_lock()
        else:
            print(f"Could not acquire lock for {self.file_path}")

    def copy_to_historical_then_replace_parquet_file2(self, df):
        print('BOzO')
        print(self.file_path)
        if self.lock.acquire_lock():
            try:
                if os.path.exists(self.file_path):
                    # Create the historical directory if it doesn't exist
                    # historical_dir = os.path.join(os.path.dirname(self.file_path), 'historical')
                    # if not os.path.exists(historical_dir):
                    #     os.makedirs(historical_dir)
                    
                    # # Format the timestamp
                    # timestamp = datetime.utcnow().strftime("_%Y%m%d-%H%M%S")
                    # historical_file_path = os.path.join(historical_dir, os.path.basename(self.file_path) + timestamp)
                    
                    # # Copy the existing file to the historical directory
                    # shutil.copy(self.file_path, historical_file_path)
                
                # Write the DataFrame to the original file location, replacing it
                    df_write_to_pq(df, self.file_path)
            finally:
                self.lock.release_lock()
        else:
            print(f"Could not acquire lock for {self.file_path}")

    def make_simple_historical_then_write_over_parquet_file2(self, df):
        if self.lock.acquire_lock():
            try:
                # Determine the directory for historical data and create it if it doesn't exist
                historical_dir = os.path.join(os.path.dirname(self.file_path), "historical")
                os.makedirs(historical_dir, exist_ok=True)

                # Create a UTC timestamped filename
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                versioned_file_path = os.path.join(historical_dir, f"{timestamp}.parquet")

                # Write the dataframe to a parquet file with a UTC timestamp
                df.to_parquet(versioned_file_path, index=False)

                # Create or update the symbolic link to point to the latest version
                symlink_path = os.path.join(os.path.dirname(self.file_path), "latest.parquet")
                if os.path.islink(symlink_path):
                    os.unlink(symlink_path)
                os.symlink(versioned_file_path, symlink_path)
            finally:
                self.lock.release_lock()
        else:
            print(f"Could not acquire lock for {self.file_path}")

class ParquetFileWithLock:
    def __init__(self, file_path, lock_path=None):
        self.file_path = file_path
        self.lock_path = lock_path if lock_path else f"{file_path}.lock"

    def read_parquet_file_or_create_standard_scraper_dataframe(self):
        with FileLock(self.lock_path, timeout=10):
            if os.path.exists(self.file_path):
                return pd.read_parquet(self.file_path)
            else:
                return pd.DataFrame(columns=["FILE", "FILESIZE", "CREATION_TIME", "MODIFICATION_TIME", "ISLINK", "TARGET"])

    def read_parquet_file(self):
        with FileLock(self.lock_path, timeout=10):
            if os.path.exists(self.file_path):
                return pd.read_parquet(self.file_path)
            else:
                print(f"No file @ {self.file_path}")

    def write_parquet_file(self, df):
        with FileLock(self.lock_path, timeout=10):
            df.to_parquet(self.file_path, index=False)

    def copy_to_historical_then_replace_parquet_file(self, df):
        with FileLock(self.lock_path, timeout=10):
            if os.path.exists(self.file_path):
                # Create the historical directory if not exists
                historical_dir = os.path.join(os.path.dirname(self.file_path), 'historical')
                if not os.path.exists(historical_dir):
                    os.makedirs(historical_dir)
                
                # Format the timestamp
                timestamp = datetime.utcnow().strftime("_%Y%m%d-%H%M%S")
                historical_file_path = os.path.join(historical_dir, os.path.basename(self.file_path) + timestamp)
                
                # Copy the existing file to the historical directory
                shutil.copy(self.file_path, historical_file_path)
            
            # Write the DataFrame to the original file location, replacing it
            df.to_parquet(self.file_path, index=False)

    def make_simple_historical_then_write_over_parquet_file(self, df):
        with FileLock(self.lock_path, timeout=10):
            # Determine the directory for historical data and create if it doesn't exist
            historical_dir = os.path.join(os.path.dirname(self.file_path), "historical")
            os.makedirs(historical_dir, exist_ok=True)

            # Create a UTC timestamped filename
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            versioned_file_path = os.path.join(historical_dir, f"{timestamp}.parquet")

            # Write the dataframe to a parquet file with a UTC timestamp
            df.to_parquet(versioned_file_path, index=False)

            # Create or update the symbolic link to point to the latest version
            symlink_path = os.path.join(os.path.dirname(self.file_path), "latest.parquet")
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)
            os.symlink(versioned_file_path, symlink_path)

def df_write_to_pq(df, file_path, metadata=None):
    """
    Writes a DataFrame to a Parquet file using a Singleton lock.

    Args:
        df : pd.DataFrame - The DataFrame to write.
        file_path (str): Target Parquet file path.
        metadata (dict, optional): Custom metadata to include in the Parquet file.
    """
    
    # Create a Singleton lock with the identifier based on the file path
    lock = Singleton(file_path)
    
    # Try to acquire the lock
    if lock.acquire_lock():
        try:
            # Convert DataFrame to Arrow Table
            table = pa.Table.from_pandas(df)
            
            # Update metadata if provided
            if metadata is not None:
                existing_metadata = table.schema.metadata or {}
                updated_metadata = {**existing_metadata, **{k.encode('utf-8'): v.encode('utf-8') for k, v in metadata.items()}}
                table = table.replace_schema_metadata(updated_metadata)
            
            # Write table to Parquet file
            pq.write_table(table, file_path)
            # print(f"DataFrame written to {file_path}.")
        
        except Exception as e:
            print(f"Error writing DataFrame to Parquet: {e}")
        
        finally:
            # Release the lock
            lock.release_lock()
    else:
        print(f"Could not acquire lock for {file_path}. Skipping write.")

class sequenceWork:
    def get_sequence(df, sequence_name):
        return df[df['Sequence'] == sequence_name]

    def get_sequence_member(df, sequence_name, position):
        member = df[(df['Sequence'] == sequence_name) & (df['Position'] == position)]
        if member.empty:
            raise ValueError("Member does not exist")
        return member

    def check_missing_files(df, sequence_name):
        sequence_df = get_sequence(df, sequence_name)
        highest_position = sequence_df['Position'].max()
        entries_count = sequence_df.shape[0]
        expected_count = highest_position - sequence_df['Position'].min() + 1  # Assuming positions start at 1 and are continuous

        if expected_count == entries_count:
            return "No missing files."
        else:
            missing_count = expected_count - entries_count
            return f"{missing_count} files are missing."

    def detailed_missing_files_info(df, sequence_name):
        sequence_df = get_sequence(df, sequence_name).sort_values(by='Position')
        full_range = set(range(sequence_df['Position'].min(), sequence_df['Position'].max() + 1))
        actual_positions = set(sequence_df['Position'])
        missing_positions = list(full_range - actual_positions)
        missing_positions.sort()
        
        return missing_positions if missing_positions else "No missing files."

    def extract_sequence_info(file_path):
        """
        Extracts SEQUENCENAME and SEQUENCEPOSITION from a given file path.
        Returns None for both if the file is not a sequence member.
        """
        # Regex to find the sequence pattern
        match = re.search(r'(.+[/\\].+)(\.\d+)(\.\w+)$', file_path)
        if match:
            base, position_str, ext = match.groups()
            position = int(position_str.lstrip('.'))
            sequence_name = f"{base}.%0{len(position_str)-1}d{ext}"
            return sequence_name, position
        return None, None

    def add_sequence_info(df):
        """
        Adds SEQUENCENAME and SEQUENCEPOSITION columns to the DataFrame,
        populating them based on the FILE column for sequence members.
        Non-members receive empty strings for both new columns.

        Args:
            df (pd.DataFrame): DataFrame containing a 'FILE' column with file paths.
        
        Returns:
            pd.DataFrame: The updated DataFrame with sequence information added.
        """
        # Initialize new columns with empty strings
        df['SEQUENCENAME'] = ''
        df['SEQUENCEPOSITION'] = ''
        df['PADDING'] = ''

        # Compile a regex pattern to match the sequence logic
        pattern = re.compile(r'(?P<before>.*[/\\])(?P<name>.*?)(?P<sep>[.])(?P<position>\d+)(?P<after>\.[^.]+)$')

        # Iterate through each file path in the DataFrame
        for index, row in df.iterrows():
            match = pattern.search(row['FILE'])
            if match:
                # Extract matched groups
                groups = match.groupdict()
                name = groups['name']
                sep = groups['sep']
                position = groups['position']
                before = groups['before']
                after = groups['after']

                # Determine the sequence name with %0d notation for the position
                position_length = len(position)
                sequence_name = f"{before}{name}{sep}%0{position_length}d{after}"
                sequence_position = position  # Keep position as string

                # Update the DataFrame
                df.at[index, 'SEQUENCENAME'] = sequence_name
                df.at[index, 'SEQUENCEPOSITION'] = sequence_position
                df.at[index, 'PADDING'] = position_length

        return df

    def add_sequence_info_v2(df, whitelist=None):
        """
        Adds SEQUENCENAME and SEQUENCEPOSITION columns to the DataFrame,
        populating them based on the FILE column for sequence members.
        Non-members receive empty strings for both new columns.

        Args:
            df (pd.DataFrame): DataFrame containing a 'FILE' column with file paths.
            whitelist (list of str, optional): List of file extensions to process, e.g., ['.jpg', '.png'].
        
        Returns:
            pd.DataFrame: The updated DataFrame with sequence information added.
        """
        # Initialize new columns with empty strings
        df['SEQUENCENAME'] = ''
        df['SEQUENCEPOSITION'] = ''
        df['PADDING'] = ''

        # Set default whitelist if none provided
        if whitelist is None:
            whitelist = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.dpx', '.cin', '.tx', '.ass', '.vdb', '.sgi', '.tga']  # Default file extensions

        # Convert whitelist to lowercase for case-insensitive comparison
        whitelist = [ext.lower() for ext in whitelist]

        # Compile a regex pattern to match the sequence logic
        pattern = re.compile(r'(?P<before>.*[/\\])(?P<name>.*?)(?P<sep>[.])(?P<position>\d+)(?P<after>\.[^.]+)$')
        print("Boo")
        # Iterate through each file path in the DataFrame
        for index, row in df.iterrows():
            # Extract the file extension and convert to lowercase
            file_extension = re.search(r'\.[^.]*$', row['FILE'])
            # print("File extension to check against whitelist:", file_extension)
            if file_extension and file_extension.group(0).lower() in whitelist:
                match = pattern.search(row['FILE'])
                if match:
                    # Extract matched groups
                    groups = match.groupdict()
                    name = groups['name']
                    sep = groups['sep']
                    position = groups['position']
                    before = groups['before']
                    after = groups['after']

                    # Determine the sequence name with %0d notation for the position
                    position_length = len(position)
                    sequence_name = f"{before}{name}{sep}%0{position_length}d{after}"
                    sequence_position = position  # Keep position as string

                    # Update the DataFrame
                    df.at[index, 'SEQUENCENAME'] = sequence_name
                    df.at[index, 'SEQUENCEPOSITION'] = sequence_position
                    df.at[index, 'PADDING'] = position_length

        return df

    def add_sequence_info_v3(df, whitelist=None):
        """
        Adds SEQUENCENAME and SEQUENCEPOSITION columns to the DataFrame,
        populating them based on the FILE column for sequence members.
        Non-members receive empty strings for both new columns.

        Args:
            df (pd.DataFrame): DataFrame containing a 'FILE' column with file paths.
            whitelist (list of str, optional): List of file extensions to process, e.g., ['.jpg', '.png'].
        
        Returns:
            pd.DataFrame: The updated DataFrame with sequence information added.
        """
        # Initialize new columns with empty strings
        df['SEQUENCENAME'] = ''
        df['SEQUENCEPOSITION'] = ''
        df['PADDING'] = ''

        print('BOOo1')

        # Set default whitelist if none provided
        if whitelist is None:
            whitelist = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.dpx', '.cin', '.tx', '.ass', '.vdb', '.sgi', '.tga']  # Default file extensions

        # Convert whitelist to lowercase for case-insensitive comparison
        whitelist = [ext.lower() for ext in whitelist]
        print('BOOo2')
        print(whitelist)
        print(df)

        # Compile a regex pattern to match the sequence logic
        pattern = re.compile(
            r'(?P<before>.*[/\\])'    # Path before the filename
            r'(?P<name>.*?)'          # Name of the file (non-greedy)
            r'(?P<sep>[._-])'         # Separator between name and number (allowing . _ or -)
            r'(?P<position>\d{1,20})' # Sequence number (up to 20 digits)
            r'(?P<after>\.[^.]+)$'    # File extension
        )
        print('BOOo3')

        # Iterate through each file path in the DataFrame
        for index, row in df.iterrows():
            print('BOOo4')
            # Extract just the filename from the path
            file_name = row['FILE'].split('/')[-1] if '/' in row['FILE'] else row['FILE'].split('\\')[-1]
            print(file_name)

            # Extract the file extension and convert to lowercase
            file_extension = re.search(r'\.[^.]*$', file_name)
            
            # Check if the filename has more than two periods
            if file_name.count('.') > 2:
                continue  # Skip this file if it has more than two periods in its name
            
            if file_extension and file_extension.group(0).lower() in whitelist:
                match = pattern.search(row['FILE'])
                if match:
                    # Extract matched groups
                    groups = match.groupdict()
                    name = groups['name']
                    sep = groups['sep']
                    position = groups['position']
                    before = groups['before']
                    after = groups['after']

                    # Determine the sequence name with %0d notation for the position
                    position_length = len(position)
                    sequence_name = f"{before}{name}{sep}%0{position_length}d{after}"
                    sequence_position = position  # Keep position as string

                    # Update the DataFrame
                    df.at[index, 'SEQUENCENAME'] = sequence_name
                    df.at[index, 'SEQUENCEPOSITION'] = sequence_position
                    df.at[index, 'PADDING'] = position_length

        return df

    def add_sequence_info_v4(df, whitelist=None):
        df['SEQUENCENAME'] = ''
        df['SEQUENCEPOSITION'] = ''
        df['PADDING'] = ''

        if whitelist is None:
            whitelist = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.dpx', '.cin', '.tx', '.ass', '.vdb', '.sgi', '.tga']

        whitelist = [ext.lower() for ext in whitelist]

        placeholder = 'Xa8YYT'

        for index, row in df.iterrows():
            file_path = row['FILE']
            file_extension = file_path[file_path.rfind('.'):].lower()

            if file_extension not in whitelist:
                continue

            file_path = file_path.replace(' ', placeholder)
            file_base = file_path[:file_path.rfind('.')]
            sep_index = max(file_base.rfind('_'), file_base.rfind('.'))
            if sep_index == -1:
                continue

            frame_number = file_base[sep_index + 1:]
            base_name = file_base[:sep_index]
            separator = file_base[sep_index]

            if frame_number.isdigit() and len(frame_number) > 1:
                base_name = base_name.replace(placeholder, ' ')
                sequence_name = f"{base_name}{separator}%0{len(frame_number)}d{file_extension}"
                df.at[index, 'SEQUENCENAME'] = sequence_name
                df.at[index, 'SEQUENCEPOSITION'] = frame_number
                df.at[index, 'PADDING'] = len(frame_number)
            else:
                base_name = base_name.replace(placeholder, ' ')
                df.at[index, 'SEQUENCENAME'] = ''
                df.at[index, 'SEQUENCEPOSITION'] = ''
                df.at[index, 'PADDING'] = ''

        return df

def decompose_file_paths(df):
    hierarchy_data = []

    # Decompose the file paths as before
    for path in df['FILE']:
        parts = path.split('/')
        hierarchy = {'FILE': path}  # Original file path
        
        # Decompose the path
        for i in range(1, len(parts)):
            # Construct the hierarchical path at this depth
            hierarchy_path = '/'.join(parts[:i])
            if hierarchy_path.endswith(':'):
                hierarchy_path += '/'  # To handle root drives on Windows
            # Use the hierarchy path as a key and the remainder as a value
            hierarchy[hierarchy_path] = '/'.join(parts[i:])
        
        hierarchy_data.append(hierarchy)

    # Convert the list of dictionaries into a DataFrame
    decomposed_df = pd.DataFrame(hierarchy_data)
   
    # Fill NaNs with empty strings
    decomposed_df.fillna('', inplace=True)

    # Ensure all columns are of type string
    for col in decomposed_df.columns:
        decomposed_df[col] = decomposed_df[col].astype(str)

    # Concatenate the original df with decomposed_df. 
    # Ensure there's no overlap in columns except for 'FILE', which we'll use as an identifier.

    combined_df = pd.merge(df, decomposed_df, on='FILE', how='left')

    # Ensure all columns are of type string
    # for col in combined_df.columns:
    #     combined_df[col] = combined_df[col].astype(str)

    return combined_df

def find_deepest_common_parent_by_longest_header(decomposed_df):
    """
    Identify the deepest common parent directory by finding the column
    with the longest header among those that don't contain any empty fields.

    Args:
        decomposed_df (pd.DataFrame): DataFrame with hierarchical path components as columns.

    Returns:
        str: The column name representing the deepest common parent directory.
    """
    # Filter columns to those without any empty strings
    non_empty_columns = [col for col in decomposed_df.columns if not decomposed_df[col].eq('').any()]

    # Find the column with the longest header, which represents the deepest directory
    deepest_common_parent = max(non_empty_columns, key=len, default=None)

    return deepest_common_parent

def create_source_parquet(file_path):
    """
    Initializes a Parquet file with default headers. If the file already exists, it will be overwritten.

    Args:
        file_path (str): The path where the Parquet file will be created.
    """
    default_columns = ["FILE", "FILESIZE", "CREATION_TIME", "MODIFICATION_TIME", "ISLINK", "TARGET"]
    df = pd.DataFrame(columns=default_columns)
    
    # Optionally, you could add initial data to df here before saving
    
    df.to_parquet(file_path)
    print(f"Source Parquet file initialized at {file_path} with default headers.")

def source_create_and_or_read(file_path):
    parquet_manager = ParquetFileWithLock(file_path)
    df = parquet_manager.read_parquet_file_or_create_standard_scraper_dataframe()

    if df.empty:
        parquet_manager.write_parquet_file(df)  # Writes an empty DataFrame with default columns

    else:
        print(f"Loaded Parquet file from {file_path}.")
    
    return df

def source_create_and_or_read_confirm(file_path):
    parquet_manager = ParquetFileWithLock(file_path)
    df = parquet_manager.read_parquet_file_or_create_standard_scraper_dataframe()

    if df.empty:
        response = input(f"File {file_path} not found. Would you like to create a new source Parquet file? (y/n): ")
        if response.lower() == 'y':
            parquet_manager.write_parquet_file(df)  # Writes an empty DataFrame with default columns
            print(f"New source Parquet file created at {file_path}.")
        else:
            print("Exiting without creating a new file.")
            return None
    else:
        print(f"Loaded Parquet file from {file_path}.")
    
    return df

def ensure_matching_headers(existing_df, new_data_df, parquet_file_path):
    """
    Ensures that both the existing DataFrame and the new DataFrame have matching headers,
    adding any missing columns where necessary and initializing them with empty strings.
    This version addresses DataFrame fragmentation and initializes new columns correctly.

    Args:
        existing_df (pd.DataFrame): The DataFrame loaded from the Parquet file.
        new_data_df (pd.DataFrame): The new data DataFrame.
        parquet_file_path (str): Path to the Parquet file for updating the schema.
    """
    # Convert sets to lists to avoid "columns cannot be a set" ValueError
    missing_in_existing = list(set(new_data_df.columns) - set(existing_df.columns))
    missing_in_new_data = list(set(existing_df.columns) - set(new_data_df.columns))
    
    # Initialize missing columns in existing_df with empty strings
    for col in missing_in_existing:
        existing_df[col] = ''
    
    # Initialize missing columns in new_data_df with empty strings
    for col in missing_in_new_data:
        new_data_df[col] = ''
    
    # Ensure the columns order matches in both DataFrames before concatenation
    new_data_df = new_data_df[existing_df.columns]
    
    # Save the updated existing_df back to the Parquet file
    existing_df.to_parquet(parquet_file_path, index=False)

def remove_matching_entries_based_on_parent(new_data_df, existing_df, column):
    """
    Removes rows from new_data_df that have matching entries in the specified column of existing_df.

    Args:
        new_data_df (pd.DataFrame): The DataFrame containing the new data.
        existing_df (pd.DataFrame): The DataFrame loaded from the existing Parquet file.
        column (str): The column name based on which the matching needs to be done.
    
    Returns:
        pd.DataFrame: Updated new_data_df with matching rows removed.
    """
    if column in new_data_df.columns:
        # Convert column to string to ensure .str operations work
        new_data_df[column] = new_data_df[column].astype(str)
        # existing_df[column] = existing_df[column].astype(str)
        
    # Ensure no leading/trailing spaces and case-insensitivity for the comparison column

    existing_df[column] = existing_df[column].str.strip().str.lower()
    new_data_df[column] = new_data_df[column].str.strip().str.lower()
    
    # Find the values in the new data column that match any in the existing data column
    matches = new_data_df[column].isin(existing_df[column])
    
    # Remove rows from new_data_df that have matches in existing_df
    culled_df = new_data_df[~matches].reset_index(drop=True)

    return culled_df

def source_concat_dedupe_clean_and_write(dfs, file_path, metadata=None):
    """
    Concatenates multiple DataFrames, performs cleaning operations including replacing NaN values,
    updates metadata, and writes the result to a Parquet file.

    Args:
        dfs (list of pd.DataFrame): DataFrames to concatenate.
        file_path (str): Target Parquet file path.
        metadata (dict, optional): Custom metadata to include in the Parquet file.
    """
    # Concatenate DataFrames
    combined_df = pd.concat(dfs, ignore_index=True)

    # Drop duplicates based on the 'FILE' column only
    combined_df.drop_duplicates(subset=['FILE'], inplace=True)

    combined_df = combined_df.astype(str)

    # Convert DataFrame to PyArrow Table for metadata addition
    table = pa.Table.from_pandas(combined_df)
    
    # Update metadata if provided
    if metadata is not None:
        existing_metadata = table.schema.metadata or {}
        updated_metadata = {**existing_metadata, **{k.encode('utf-8'): v.encode('utf-8') for k, v in metadata.items()}}
        table = table.replace_schema_metadata(updated_metadata)
    
    # Write table to Parquet file
    pq.write_table(table, file_path)
    print(f"DataFrame written to {file_path}.")

def read_parquet_or_initialize(path, schema=None):
    """
    Reads a Parquet file into a DataFrame. If the file does not exist, returns an empty DataFrame with an optional schema.

    Args:
        path (str): The file path to the Parquet file.
        schema (dict, optional): A dictionary defining the schema of the DataFrame to be created if the file does not exist.
                                The keys should be column names and the values should be Pandas dtype objects.

    Returns:
        pd.DataFrame: The DataFrame read from the Parquet file or an empty DataFrame with the specified schema.
    """
    if os.path.exists(path):
        # File exists, read the Parquet file
        df = pd.read_parquet(path)
    else:
        # File does not exist, prepare an empty DataFrame with the specified schema if provided
        if schema is not None:
            # Initialize an empty DataFrame with the specified schema
            df = pd.DataFrame({col: pd.Series(dtype=typ) for col, typ in schema.items()})
        else:
            # No schema provided, return an empty DataFrame without specific columns or types
            df = pd.DataFrame()
    
    return df

def source_concat_clean_and_write(dfs, file_path, metadata=None):
    """
    Concatenates multiple DataFrames, performs cleaning operations including replacing NaN values,
    updates metadata, and writes the result to a Parquet file.

    Args:
        dfs (list of pd.DataFrame): DataFrames to concatenate.
        file_path (str): Target Parquet file path.
        metadata (dict, optional): Custom metadata to include in the Parquet file.
    """
    # Concatenate DataFrames
    combined_df = pd.concat(dfs, ignore_index=True)

    # Clean NaN values - replacing with empty strings or another placeholder as needed
    # combined_df.fillna('', inplace=True)

    # Convert DataFrame to PyArrow Table for metadata addition
    table = pa.Table.from_pandas(combined_df)
    
    # Update metadata if provided
    if metadata is not None:
        existing_metadata = table.schema.metadata or {}
        updated_metadata = {**existing_metadata, **{k.encode('utf-8'): v.encode('utf-8') for k, v in metadata.items()}}
        table = table.replace_schema_metadata(updated_metadata)
    
    # Write table to Parquet file
    pq.write_table(table, file_path)
    print(f"DataFrame written to {file_path}.")

def df_write_to_pq_with_history(df, file_path, metadata=None):
    """
    Writes DataFrame to a Parquet file with optional metadata. Saves a historical copy
    in a 'historical' subdirectory without affecting the original file's write process.

    Args:
        df: DataFrame to write.
        file_path (str): Target Parquet file path.
        metadata (dict, optional): Custom metadata to include in the Parquet file.
    """
    table = pa.Table.from_pandas(df)

    # Original metadata handling for the file being written
    if metadata is not None:
        existing_metadata = table.schema.metadata or {}
        updated_metadata = {**existing_metadata, **{k.encode('utf-8'): v.encode('utf-8') for k, v in metadata.items()}}
        table = table.replace_schema_metadata(updated_metadata)
    
    # Write the table to Parquet file as before
    pq.write_table(table, file_path)
    print(f"DataFrame written to {file_path}.")

    # For historical copy: Prepare metadata including timestamp
    historical_metadata = {
        'timestamp': datetime.now().isoformat(),
        # Add more metadata for historical context as needed
    }
    
    # Merge original metadata with historical metadata for the copy
    if metadata is not None:
        historical_metadata.update(metadata)
    
    historical_metadata = {**{k.encode('utf-8'): v.encode('utf-8') for k, v in historical_metadata.items()}}
    historical_table = table.replace_schema_metadata(historical_metadata)
    
    # Ensure historical directory exists
    dir_name, file_name = os.path.split(file_path)
    historical_dir = os.path.join(dir_name, 'historical')
    os.makedirs(historical_dir, exist_ok=True)

    # Save a copy to the historical directory with a timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    historical_file_path = os.path.join(historical_dir, f"{timestamp}_{file_name}")
    pq.write_table(historical_table, historical_file_path)
    
    print(f"Copy saved in historical directory: {historical_file_path}")

def create_partitioned_parquet(original_file_path, partition_col, output_dir, row_group_cols=None):
    """
    Creates copies of a Parquet file with different partitioning and/or row groupings.

    Args:
        original_file_path (str): The path to the original Parquet file.
        partition_col (str): The column name to use for partitioning.
        output_dir (str): The directory to save the partitioned Parquet files.
        row_group_cols (list[str], optional): A list of column names to use for row groupings.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Read the original Parquet file into a DataFrame
    df = pd.read_parquet(original_file_path)

    # Ensure row_group_cols is a list, even if None or a single string is provided
    if row_group_cols is None:
        row_group_cols = []
    elif isinstance(row_group_cols, str):
        row_group_cols = [row_group_cols]

    # If row group columns are provided, re-order the DataFrame to have these columns first
    if row_group_cols:
        df = df[[partition_col] + row_group_cols + [col for col in df.columns if col not in row_group_cols and col != partition_col]]
    
    # Convert DataFrame to PyArrow Table
    table = pa.Table.from_pandas(df)
    
    # Write the table to a partitioned Parquet file/dataset
    pq.write_to_dataset(table, root_path=output_dir, partition_cols=[partition_col])

    print(f"Partitioned Parquet files created in '{output_dir}' directory.")
