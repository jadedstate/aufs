import os
from datetime import datetime
import pandas as pd
import fnmatch
import hashlib
import json
from pathlib import Path

from .config import F_root_path
from .parquet_tools import df_write_to_pq

class defaultScrapeToParquet:
    def __init__(self, job=None):
        self.scraper = FileSystemScraper()
        self.root = Path(F_root_path())
        if job is None:
            self.job = 'internal-staging'
        else:
            self.job = job
        self.client, self.project = self.job.split('-')
        # print("Have we set up to scrape?")
        # print(self.root)

    def scrape_and_prepare_data(self, root_paths):
        # print("We did the setup, now, did we ask for scraping to happen?")

        self.root_paths = root_paths
        # print(self.root_paths)
        self.data_df = self.scraper.scrape_directories(self.root_paths)
        self.scrape_time = datetime.utcnow()
        self.scrape_id = self.generate_scrape_id(self.root_paths, self.scrape_time)
        # print("Ok, did we do the scrape???")


        # Optional: store metadata in a DataFrame or a dedicated structure
        self.metadata = {
            'SCRAPEID': self.scrape_id,
            'SCRAPE_TIME': self.scrape_time.isoformat(),
            'PATHS': self.root_paths
        }
        # print(self.scrape_id)
        self.data_df = self.add_hashedfile_column(self.data_df, 'FILE')

        self.save_to_parquet()
        return self.parquet_name

    def add_hashedfile_column(self, df, column_name_for_hashing, noHashNonStringFields=True):
        if column_name_for_hashing in df.columns:
            # Handle non-string fields based on noHashNonStringFields flag
            if df[column_name_for_hashing].dtype != 'object' and noHashNonStringFields:
                print(f"The column '{column_name_for_hashing}' is not of type string. Marking as 'noHash'.")
                df['HASHEDFILE'] = 'noHash'
            else:
                if df[column_name_for_hashing].dtype != 'object':
                    print(f"The column '{column_name_for_hashing}' is not of type string. Attempting to convert to string.")
                    df[column_name_for_hashing] = df[column_name_for_hashing].astype(str)
                
                # Create HASHEDFILE column by hashing the specified column's values
                def hash_value(value):
                    try:
                        # Ensure value is a string and trim spaces
                        value = str(value).strip()
                        # Create a hash object
                        hash_obj = hashlib.sha256()
                        hash_obj.update(value.encode('utf-8'))
                        return hash_obj.hexdigest()
                    except Exception as e:
                        return 'noHash'
                
                df['HASHEDFILE'] = df[column_name_for_hashing].apply(hash_value)
        else:
            print(f"Column '{column_name_for_hashing}' not found in DataFrame. HASHEDFILE column will not be created.")
            df['HASHEDFILE'] = 'noColumn'
        
        return df

    def generate_scrape_id(self, paths, scrape_time):
        hash_input = json.dumps({"paths": paths, "time": scrape_time.isoformat()})
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def save_to_parquet(self):
        # pass
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = Path(self.root / "fs_main/parquet/source_files/source_main/sparking/source_main_all/start")
        # job_path = Path(self.root / "jobs/IO/work/tracking" / self.job / "filesystem/source_main") # will use this later
        self.parquet_name = file_path / f"{timestamp}-{self.scrape_id}.parquet"
        # print(self.metadata)
        # print("That was metadata")

        # os.makedirs(job_path, exist_ok=True)
        os.makedirs(file_path, exist_ok=True)

        df_write_to_pq(self.data_df, self.parquet_name)

class FileSystemScraper:
    def __init__(self):
        pass  # No initial path needed anymore

    def process_files(self, paths):
        """
        Process a list of file paths, extracting relevant data for each.
        This method can be used directly by external processes with absolute paths.
        """
        data = [self.process_entry(path) for path in paths]
        return self.format_as_dataframe(data)

    def process_entry(self, path):
        """
        Process a single file or directory entry to extract relevant data.
        """
        # print('BooWho')
        if os.path.islink(path):
            target, target_type, size = self.resolve_target(path)
        else:
            target_type = 'no'
            target = ''
            size = os.path.getsize(path) if os.path.exists(path) else 'N/A'

        creation_time = datetime.fromtimestamp(os.path.getctime(path)).strftime('%Y-%m-%d %H:%M:%S') if os.path.exists(path) else 'N/A'
        modification_time = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S') if os.path.exists(path) else 'N/A'
        status = 'online'

        return path, size, creation_time, modification_time, target_type, target, status

    def resolve_target(self, link_path):
        """
        Resolve the link's target without altering its relative or absolute nature and determine its size.
        Determines if the resolved target is a file, directory, or of an unknown type.
        
        Parameters:
        - link_path (str): The path to the symbolic link.
        
        Returns:
        - tuple: A tuple containing the resolved path to the target (untouched), its type ('file', 'dir', 'unknown'), and its size if applicable.
        """
        # Read the target of the symbolic link
        target_path = os.readlink(link_path)
        
        # Compute the full path to the target for the purpose of type checking and size determination
        full_target_path = os.path.abspath(os.path.join(os.path.dirname(link_path), target_path))
        
        # Determine if the target is a file, directory, or unknown, using the full path for this check
        if os.path.isdir(full_target_path):
            target_type = 'dir'
            size = '0'  # Directories don't have a 'size' in the same way files do
        elif os.path.isfile(full_target_path):
            target_type = 'file'
            size = os.path.getsize(full_target_path)
        else:
            target_type = 'unknown'
            size = '1'

        # Return the original target path as resolved (preserving its relative or absolute nature), the target type, and size
        return target_path, target_type, size

    def format_as_dataframe(self, data):
        """
        Format the scraped or processed data as a pandas DataFrame,
        then clean up the DataFrame according to specified rules,
        including standardizing path separators after ensuring all
        columns are of the correct type.
        """
        df = pd.DataFrame(data, columns=["FILE", "FILESIZE", "CREATION_TIME", "MODIFICATION_TIME", "ISLINK", "TARGET", "STATUS"])
        
        # Convert 'N/A' and other placeholders to appropriate values or data types
        df['FILESIZE'] = pd.to_numeric(df['FILESIZE'], errors='coerce').fillna(0).astype(int)
        df['ISLINK'] = df['ISLINK'].fillna('no').astype(str)
        df['TARGET'] = df['TARGET'].fillna('').astype(str)  # Ensuring string type for TARGET
        
        # Specifying the datetime format
        datetime_format = '%Y-%m-%d %H:%M:%S'

        # Assuming '1999-12-31 23:59:59' is used as a placeholder for invalid or missing datetimes
        default_datetime = pd.to_datetime('1999-12-31 23:59:59', format=datetime_format)

        # Convert 'CREATION_TIME' and 'MODIFICATION_TIME' to datetime, specifying the format
        df['CREATION_TIME'] = pd.to_datetime(df['CREATION_TIME'], errors='coerce', format=datetime_format).fillna(default_datetime)
        df['MODIFICATION_TIME'] = pd.to_datetime(df['MODIFICATION_TIME'], errors='coerce', format=datetime_format).fillna(default_datetime)

        # Standardize path separators in FILE and TARGET columns to "/"
        df['FILE'] = df['FILE'].str.replace('\\', '/').str.replace('//', '/')
        df['TARGET'] = df['TARGET'].replace('\\', '/').str.replace('//', '/')
        
        return df
        
    def scrape_directory(self, root_path):
        """
        Scrape filesystem data starting from a root directory path, focusing on files and links only,
        while excluding paths that match any of a list of patterns.
        """
        # Define the patterns to exclude
        exclude_patterns = [
            '*/jobs/IO/work/*',
            '*/jobs/PROD/*',
            '*/data/thumbs*',
            '*/.*',
            # Add more patterns as needed
        ]
        paths = []

        for root, dirs, files in os.walk(root_path, followlinks=False):
            # Exclude specific directories from being walked into by checking against all patterns
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(os.path.join(root, d), pattern) for pattern in exclude_patterns)]

            # Process files directly under each directory
            for file in files:
                path = os.path.join(root, file)
                # Check if the file matches any of the exclusion patterns
                if not any(fnmatch.fnmatch(path, pattern) for pattern in exclude_patterns):
                    paths.append(path)
            
            # Check each directory to see if it's a link, and if so, add it
            # Ensuring it does not match any of the exclusion patterns
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                if os.path.islink(dir_path) and not any(fnmatch.fnmatch(dir_path, pattern) for pattern in exclude_patterns):
                    paths.append(dir_path)
        
        return self.process_files(paths)

    def scrape_directories(self, root_paths, return_paths=False):
        # print("BOO24")
        exclude_patterns = [
            '*/jobs/IO/work/*',
            '*/jobs/PROD/*',
            '*/moviemaking/*',
            '*/IO/from*',
            '*/IO/to*',
            '*/data/setup*',
            '*/data/thumbs*',
            '*/.*'
            # Add more patterns as needed
        ]
        all_scraped_paths = []
        for root_path in root_paths:
            for root, dirs, files in os.walk(root_path, followlinks=False):
                # Exclude specific directories from being walked into by checking against all patterns
                dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(os.path.join(root, d), pattern) for pattern in exclude_patterns)]

                # Process files directly under each directory
                for file in files:
                    path = os.path.join(root, file)
                    # Check if the file matches any of the exclusion patterns
                    if not any(fnmatch.fnmatch(path, pattern) for pattern in exclude_patterns):
                        all_scraped_paths.append(path)

                # Check each directory to see if it's a link, and if so, add it
                # Ensuring it does not match any of the exclusion patterns
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    if os.path.islink(dir_path) and not any(fnmatch.fnmatch(dir_path, pattern) for pattern in exclude_patterns):
                        all_scraped_paths.append(dir_path)  # Correctly append the directory path

        data_df = self.process_files(all_scraped_paths)
        # print(data_df)

        if return_paths:
            return data_df, all_scraped_paths
        return data_df
