import os
import shutil
from pathlib import Path

class DirectoryScraper:
    def __init__(self):
        pass

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
