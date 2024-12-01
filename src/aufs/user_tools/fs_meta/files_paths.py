# files_paths.py

import os
import platform
from pathlib import Path
import re
import tempfile
import pandas as pd
import time
from datetime import datetime, timedelta

class Singleton:
    def __init__(self, identifier, lock_age_limit=60, force=False):
        self.lock_file = os.path.join(tempfile.gettempdir(), f"{identifier}.lock")
        self.lock_age_limit = timedelta(seconds=lock_age_limit)
        self.force = force

    def check_lock(self):
        if os.path.exists(self.lock_file):
            if self.force:
                print("Force flag is set. Ignoring existing lock and acquiring new one.")
                os.remove(self.lock_file)
                return False
            with open(self.lock_file, 'r') as file:
                timestamp = datetime.fromtimestamp(float(file.read()))
            if datetime.now() - timestamp > self.lock_age_limit:
                print("Lock file is stale. Removing and acquiring new lock.")
                os.remove(self.lock_file)
                return False
            return True
        return False

    def acquire_lock(self):
        if not self.check_lock():
            with open(self.lock_file, 'w') as file:
                file.write(str(time.time()))
            # print("Lock acquired.")
            return True
        else:
            print("Lock is currently held by another process.")
            return False

    def release_lock(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
            # print("Lock released.")

class FileStatusChecker:
    def __init__(self, df, check_column='FILE', status_column='STATUS'):
        """
        Initialize the FileStatusChecker with a DataFrame and optional column names.
        
        :param df: pandas DataFrame
        :param check_column: Name of the column containing file paths (defaults to 'FILE')
        :param status_column: Name of the column where the status will be recorded (defaults to 'STATUS')
        """
        self.df = df
        self.check_column = check_column
        self.status_column = status_column

    def process(self):
        """
        Processes the DataFrame to check the existence of files and update their status accordingly.
        
        :return: Modified DataFrame or original DataFrame if check column is missing
        """
        if self.check_column not in self.df.columns:
            print("Nothing to check here.")
            return self.df

        # Ensure the status column exists
        if self.status_column not in self.df.columns:
            self.df[self.status_column] = None

        # Check file existence and update status
        for index, row in self.df.iterrows():
            file_path = row[self.check_column]
            try:
                # Minimal disk access, just checking existence
                if os.path.exists(file_path):
                    self.df.at[index, self.status_column] = 'online'
                else:
                    self.df.at[index, self.status_column] = 'offline'
            except Exception as e:
                # Handle any exception by marking as 'offline'
                self.df.at[index, self.status_column] = 'offline'

        return self.df

def extract_file_paths(file_path, extensions):
    # print("extraction underway....")
    # Compile a regex pattern to match the file paths with the given extensions
    pattern = re.compile(r'\b\w:.*?\.(?:' + '|'.join(extensions) + ')', re.IGNORECASE)
    # print("patterns for matching to get file paths are: ")
    # print(pattern)
    
    # List to store matched paths
    matched_paths = []
    
    # Read the file and search for matches
    with open(file_path, 'r') as file:
        for line in file:
            matches = pattern.findall(line)
            if matches:
                matched_paths.extend(matches)
    
    return matched_paths

def root_F_path_replace_list(paths, root_path):
    os_path_replacements = {
        'Windows': r'F:/',
        'Linux': r'/mnt/localF/',
        'Darwin': r'/Volumes/localF/'
    }
    current_os = next(key for key, value in os_path_replacements.items() if value == root_path)
    print(f"Current OS: {current_os}")

    def adjust_path(path):
        path = path.replace('\\', '/')
        while '//' in path and not path.startswith('http://'):
            path = path.replace('//', '/')
        for os, path_rep in os_path_replacements.items():
            if os != current_os:
                path = path.replace(path_rep, os_path_replacements[current_os])
        return path

    return [adjust_path(path) for path in paths]

def root_F_path_replace_df(df, headers, root_path):
    os_path_replacements = {
        'Windows': r'F:/',
        'Linux': r'/mnt/localF/',
        'Darwin': r'/Volumes/localF/'
    }
    # Identify the current root_path key by its value
    current_os = next(key for key, value in os_path_replacements.items() if value == root_path)
    print(f"Current OS: {current_os}")

    def recursive_adjust(obj):
        if isinstance(obj, str):
            # Normalize all paths to use forward slashes
            obj = obj.replace('\\', '/')
            # Ensure that we don't replace protocol separators like "http://"
            while '//' in obj and not obj.startswith('http'):
                obj = obj.replace('//', '/')
            # Replace other OS paths with the normalized path for the current OS
            for os, path in os_path_replacements.items():
                if os != current_os:
                    obj = obj.replace(path, os_path_replacements[current_os])
            return obj
        elif isinstance(obj, list):
            return [recursive_adjust(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: recursive_adjust(value) for key, value in obj.items()}
        return obj

    for header in headers:
        if header in df.columns:
            df[header] = df[header].apply(recursive_adjust)
        else:
            print(f"Column '{header}' not found in dataframe.")

    return df

def generate_target_column(src_paths, dest_paths):
    """
    Generate the TARGET column as a list of relative paths from DEST to SRC.
    """
    target_paths = []
    for src, dest in zip(src_paths, dest_paths):
        target_path = create_relative_path(src, dest)
        target_paths.append(target_path)
    
    return target_paths

def find_divergence_point(path1, path2):
    """
    Find the point of divergence between two paths.
    """
    parts1 = Path(path1).parts
    parts2 = Path(path2).parts
    min_length = min(len(parts1), len(parts2))

    for i in range(min_length):
        if parts1[i] != parts2[i]:
            return i
    return min_length

def create_relative_path(source, dest):
    """
    Create a relative path from the destination to the source.
    """
    divergence_point = find_divergence_point(source, dest)
    relative_parts = ['..'] * (len(Path(dest).parts) - divergence_point - 1)
    relative_parts.extend(Path(source).parts[divergence_point:])
    return Path(*relative_parts).as_posix()

def get_mount_point(path):
    while path != os.path.sep:
        if os.path.ismount(path):
            return path
        path = os.path.abspath(os.path.join(path, os.pardir))
    return path  # Return the root directory if no mount point is found

def get_newest_csv_file(relative_directory):
    """ Return the newest CSV file in the given directory.

    Args:
        relative_directory (str): The relative path to the directory containing CSV files.

    Returns:
        str: The path to the newest CSV file in the directory.
    """
    # Resolve the absolute path from the relative directory
    directory = os.path.abspath(relative_directory)

    csv_files = [file for file in os.listdir(directory) if file.endswith('.csv')]
    full_paths = [os.path.join(directory, file) for file in csv_files]

    # Handle the case where there are no CSV files in the directory
    if not full_paths:
        return None

    return max(full_paths, key=os.path.getctime)

class PathNormalizer:
    @staticmethod
    def normalize_path(path):
        if not path:
            return path
        # Convert to absolute path if necessary
        path = os.path.abspath(path)
        # Replace backslashes with forward slashes for consistency
        return path.replace('\\', '/')

def find_dirs_n_subdirs_below(base_path, n):

    
    """
    Returns a list of all directories that are 'n' or fewer subdirectories
    below the specified base_path. It includes the absolute path to each directory.

    :param base_path: The base directory to start the search from.
    :param n: The number of subdirectory levels below the base_path to include.
    :return: A list of absolute paths to the directories up to 'n' levels deep.
    """
    base_path = os.path.expandvars(base_path)  # Expand environment variables in path
    mount_point = get_mount_point(base_path)
    target_path = os.path.join(mount_point, 'jobs')  # Assuming base_path includes '$mount/jobs'
    
    dirs_up_to_n_levels_deep = []

    for root, dirs, files in os.walk(target_path):
        # Calculate the depth of the current root directory relative to target_path
        depth = root[len(target_path):].count(os.path.sep)

        # If the depth is less than or equal to 'n', add the directory to the list
        if depth <= n:
            dirs_up_to_n_levels_deep.append(root)

            # If the current directory is at depth 'n', do not traverse deeper
            if depth == n:
                dirs[:] = []  # Clearing the dirs list prevents os.walk from descending into subdirectories

    return dirs_up_to_n_levels_deep

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

def create_symlinks(dataframe, search_strings, destination_dir):
    """
    Creates symlinks in the specified destination directory for files
    in the dataframe whose DOTEXTENSION matches any of the given search strings.
    
    :param dataframe: Pandas DataFrame with columns 'DOTEXTENSION' and 'FILE'.
    :param search_strings: List of strings to search for in the 'DOTEXTENSION' column.
    :param destination_dir: Path to the directory where symlinks will be created.
    """
    # Ensure the destination directory exists
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    
    # Filter the dataframe for rows where 'DOTEXTENSION' matches any search string
    filtered_df = dataframe[dataframe['DOTEXTENSION'].isin(search_strings)]
    print(filtered_df)
    # Create a symlink for each filtered row
    for index, row in filtered_df.iterrows():
        source_path = Path(row['FILE'])
        symlink_name = source_path.name
        target_path = Path(destination_dir) / symlink_name
        
        # Check if the symlink or file already exists to avoid overwriting or errors
        if not target_path.exists():
            os.symlink(source_path, target_path)
            print(f"Symlink created: {target_path} -> {source_path}")
        else:
            print(f"File or symlink already exists: {target_path}")

def create_symlinks_with_preset_extensions(dataframe, destination_dir):
    """
    Wrapper function for create_symlinks with hard-coded search strings.
    
    :param dataframe: Pandas DataFrame with columns 'DOTEXTENSION' and 'FILE'.
    :param destination_dir: Path to the directory where symlinks will be created.
    """
    print(dataframe)
    # Hard-coded list of search strings for DOTEXTENSION
    search_strings = ['mov', 'mp4']  # Example extensions

    # Call the original create_symlinks function with these predefined search strings
    create_symlinks(dataframe, search_strings, destination_dir)

def root_F_path_replace_payload(payload, root_path):
    os_path_replacements = {
        'Windows': r'F:/',
        'Linux': r'/mnt/localF/',
        'Darwin': r'/Volumes/localF/'
    }
    # Identify the current root_path key by its value
    current_os = next(key for key, value in os_path_replacements.items() if value == root_path)
    print(current_os)

    def recursive_adjust(obj):
        if isinstance(obj, str):
            # Normalize all paths to use forward slashes
            obj = obj.replace('\\', '/')
            # Ensure that we don't replace protocol separators like "http://"
            while '//' in obj and not obj.startswith('http'):
                obj = obj.replace('//', '/')

            # Replace other OS paths with the normalized path for the current OS
            for os, path in os_path_replacements.items():
                if os != current_os:
                    obj = obj.replace(path, os_path_replacements[current_os])
            return obj
        elif isinstance(obj, list):
            return [recursive_adjust(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: recursive_adjust(value) for key, value in obj.items()}
        return obj

    return recursive_adjust(payload)

def set_root_for_os(path):
    # Determine if the original path is a Path object
    original_is_path = isinstance(path, Path)
    
    # Convert path to string for processing if it's a Path object
    if original_is_path:
        path = str(path)
    
    # print("Converted path to string: ", path)

    # Define the OS-specific root paths
    paths = {
        'Windows': 'F:/',
        'Linux': '/mnt/localF/',
        'Darwin': '/Volumes/localF/'
    }
    
    # Detect the current OS
    current_os = platform.system()
    # print("Current OS: ", current_os)

    # Define what the current path should be replaced with
    current_path_prefix = paths[current_os]
    # print("Current path prefix for replacement: ", current_path_prefix)

    # Replace paths from other OSs with the current OS's path prefix
    for os, os_path in paths.items():
        if os != current_os:
            path = path.replace(os_path, current_path_prefix)
            # print(f"Replacing {os_path} with {current_path_prefix}")

    # print("Final path after replacements: ", path)

    # Convert back to Path if the original was a Path object
    if original_is_path:
        path = Path(path)

    return path

def set_a_render_root_for_os(path):
    # Determine if the original path is a Path object
    original_is_path = isinstance(path, Path)
    
    # Convert path to string for processing if it's a Path object
    if original_is_path:
        path = str(path)
    
    # print("Converted path to string: ", path)

    # Define the OS-specific root paths
    paths = {
        'Windows': 'R:/',
        'Linux': '/mnt/deadline-london/',
        'Darwin': '/Volumes/deadline-london/'
    }
    
    # Detect the current OS
    current_os = platform.system()
    # print("Current OS: ", current_os)

    # Define what the current path should be replaced with
    current_path_prefix = paths[current_os]
    # print("Current path prefix for replacement: ", current_path_prefix)

    # Replace paths from other OSs with the current OS's path prefix
    for os, os_path in paths.items():
        if os != current_os:
            path = path.replace(os_path, current_path_prefix)
            # print(f"Replacing {os_path} with {current_path_prefix}")

    # print("Final path after replacements: ", path)

    # Convert back to Path if the original was a Path object
    if original_is_path:
        path = Path(path)

    return path
