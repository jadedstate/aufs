# src/aufs/user_tools/scraper.py

import os
import shutil
from pathlib import Path
import pandas as pd

class DirectoryScraper:
    def __init__(self, blacklist=None):
        self.blacklist = blacklist if blacklist else []

    def scrape_directories(self, root_path):
        """
        Scrapes the directory tree from the provided root path.
        Only directories are considered, not files.
        :param root_path: The root directory to start scraping from.
        :return: A list of all absolute directory paths.
        """
        scraped_dirs = []
        for root, dirs, _ in os.walk(root_path, followlinks=False):
            for dir in dirs:
                # Absolute paths based on root_path
                dir_path = os.path.join(root, dir)
                scraped_dirs.append(dir_path)
        return scraped_dirs

    def create_replica(self, dirs, replica_root, root_path):
        """
        Create a replica of the directory structure under the replica_root.
        :param dirs: List of absolute directory paths to replicate.
        :param replica_root: The root where the replica structure will be created.
        :param root_path: The original root path to maintain the relative structure.
        """
        for dir in dirs:
            # Create the replica based on absolute paths, adjusted to start at replica_root
            replica_path = dir.replace(root_path, replica_root, 1)
            os.makedirs(replica_path, exist_ok=True)

    def zip_replica(self, replica_root, zip_file):
        """
        Zips the replica directory into the provided zip file.
        Uses shutil.make_archive to zip the entire directory.
        :param replica_root: The root of the replica directory.
        :param zip_file: The full path to the output zip file (without extension).
        """
        # Remove the .zip extension from zip_file since make_archive adds it automatically
        zip_file_without_extension = os.path.splitext(zip_file)[0]

        # Create the zip archive of the replica directory
        shutil.make_archive(zip_file_without_extension, 'zip', replica_root)

    def scrape_files(self, root_path):
        """
        Scrapes the directory tree starting from root_path and returns a list of all files,
        excluding files that match any pattern in the blacklist.
        :param root_path: The root directory to start scraping from.
        :return: A dictionary where keys are relative directory paths and values are lists of files.
        """
        scraped_files = {}
        root_path = os.path.abspath(root_path)  # Ensure absolute path for root

        for root, _, files in os.walk(root_path, followlinks=False):
            # Filter out blacklisted files
            filtered_files = [f for f in files if not any(blacklisted in f for blacklisted in self.blacklist)]

            # Get the relative directory path
            dir_path = os.path.relpath(root, root_path)

            # Store the files for this directory (if root, use special label 'Root')
            scraped_files[dir_path if dir_path != '.' else 'Root'] = filtered_files

        return scraped_files

    def files_to_dataframe(self, root_path):
        """
        Converts the scraped file structure to a pandas DataFrame.
        Each directory is represented by a column, with files listed as rows.
        :param root_path: The root directory to start scraping from.
        :return: A pandas DataFrame with directories as columns and file names as rows.
        """
        scraped_files = self.scrape_files(root_path)

        # Get the maximum number of files in any directory (for setting the number of rows)
        max_file_count = max(len(files) for files in scraped_files.values())

        # Create a dictionary to store columns for the DataFrame
        df_data = {}

        for dir_path, files in scraped_files.items():
            # Fill up with empty strings if the number of files is less than the max
            files_padded = files + [''] * (max_file_count - len(files))
            df_data[dir_path] = files_padded

        # Create and return the DataFrame
        df = pd.DataFrame(df_data)
        return df