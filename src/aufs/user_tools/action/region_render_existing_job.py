import os
import datetime
from .deadline_commands import submit_background_job
from .tile_placement import TilePlacement

class RegionRenderExistingJob:
    def __init__(self, job_id, x_tiles, y_tiles, tile_numbers=None):
        self.job_id = job_id
        self.x_tiles = x_tiles
        self.y_tiles = y_tiles
        self.tile_numbers = tile_numbers

    def submit(self, job_info_file, plugin_info_file):
        """
        Submits the tiled job using the provided job_info and plugin_info files.
        Modifies these files for each tile and submits each tile as a separate job.
        """
        # Load the job_info and plugin_info files into memory
        with open(job_info_file, 'r') as job_file:
            job_info_content = job_file.readlines()

        with open(plugin_info_file, 'r') as plugin_file:
            plugin_info_content = plugin_file.readlines()

        # Calculate base sizes and remainders
        image_width = int(self._get_value_from_plugin_info(plugin_info_content, "ImageWidth"))
        image_height = int(self._get_value_from_plugin_info(plugin_info_content, "ImageHeight"))

        x_integer = image_width // self.x_tiles
        y_integer = image_height // self.y_tiles

        x_float = image_width / self.x_tiles - x_integer
        y_float = image_height / self.y_tiles - y_integer

        x_remainder = int(round(x_float * self.x_tiles))
        y_remainder = int(round(y_float * self.y_tiles))

        last_column = self.x_tiles - 1
        last_row = self.y_tiles - 1

        # Generate tile placements
        tile_placement = TilePlacement(self.x_tiles, self.y_tiles)
        placements = tile_placement.generate_tile_placements()

        if self.tile_numbers is None:
            self.tile_numbers = list(range(self.x_tiles * self.y_tiles))

        for tile_number, row, column in placements:
            if tile_number not in self.tile_numbers:
                continue

            # Calculate Left and Right
            left = column * x_integer
            if column != last_column:
                right = (x_integer * (column + 1)) - 1
            else:
                right = (x_integer * (column + 1)) - 1 + x_remainder

            # Calculate Top and Bottom
            top = row * y_integer
            if row != last_row:
                bottom = (y_integer * (row + 1)) - 1
            else:
                bottom = (y_integer * (row + 1)) - 1 + y_remainder

            # Modify the job_info and plugin_info for this tile
            tile_job_info_content = self._modify_job_info(job_info_content, tile_number)
            tile_plugin_info_content = self._modify_plugin_info(plugin_info_content, left, right, bottom, top)

            # Write the modified content to temporary files
            temp_job_info_file = f"job_info_tile_{tile_number}.job"
            temp_plugin_info_file = f"plugin_info_tile_{tile_number}.job"

            with open(temp_job_info_file, 'w') as temp_job_file:
                temp_job_file.writelines(tile_job_info_content)

            with open(temp_plugin_info_file, 'w') as temp_plugin_file:
                temp_plugin_file.writelines(tile_plugin_info_content)

            # Submit the modified job
            result = submit_background_job(temp_job_info_file, temp_plugin_info_file)
            if result:
                print(f"Tiled job {tile_number} submitted successfully.")
            else:
                print(f"Failed to submit tiled job {tile_number}.")

            # Clean up temporary files
            os.remove(temp_job_info_file)
            os.remove(temp_plugin_info_file)

    def _modify_plugin_info(self, plugin_info_content, left, right, bottom, top):
        """
        Modifies the plugin_info content to set the region rendering parameters.
        Appends the required region rendering lines to the plugin_info file.
        """
        modified_content = plugin_info_content[:]
        modified_content.append("RegionRendering=True\n")
        modified_content.append(f"RegionLeft={left}\n")
        modified_content.append(f"RegionRight={right}\n")
        modified_content.append(f"RegionBottom={bottom}\n")
        modified_content.append(f"RegionTop={top}\n")
        return modified_content

    def _modify_job_info(self, job_info_content, region):
        """
        Modifies the job_info content for a specific tile.
        """
        modified_content = []
        utc_now = datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M')

        for index, line in enumerate(job_info_content):
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Remove BOM from the first line if present
            if index == 0 and key.startswith('\ufeff'):
                key = key.lstrip('\ufeff')

            if key == "UserName":
                modified_content.append("UserName=deadline\n")
            elif key == "MachineName":
                modified_content.append("MachineName=deadline-server\n")
            elif key == "ScheduledStartDateTime":
                modified_content.append(f"ScheduledStartDateTime={utc_now}\n")
            elif key == "BatchName":
                modified_content.append(f"BatchName={value}_Tiled\n")
            elif key == "Name":
                modified_content.append(f"Name={value}_tile_{region}\n")
            elif key == "OutputFilename0":
                modified_content.append(f"OutputFilename0=tile_{region}_{value}\n")
            else:
                modified_content.append(line)

        return modified_content

    def _get_value_from_plugin_info(self, plugin_info_content, key):
        """
        Extracts a value from the plugin_info content based on the key.
        """
        for line in plugin_info_content:
            if line.startswith(f"{key}="):
                return line.split("=")[1].strip()
        return None
