import os
import re
import subprocess

def validate_filesystem_name(filesystem_name):
    """
    Validates the filesystem name according to ObjectiveFS naming rules.
    Example rules: alphanumeric, underscores or hyphens only, 3-63 characters.
    """
    if not re.match(r"^[a-zA-Z0-9_-]{3,63}$", filesystem_name):
        return False, "Invalid name. Use 3-63 characters: letters, numbers, underscores, and hyphens only."
    return True, ""

def check_name_availability(filesystem_name, env_dir):
    """
    Checks if the filesystem name is already in use by querying ObjectiveFS.
    
    Parameters:
        filesystem_name (str): Desired filesystem name to check for availability.
        env_dir (str): Directory where ObjectiveFS environment config files are located.

    Returns:
        tuple: (bool, str) - True if available, False with a message if unavailable or error occurs.
    """
    try:
        # Set up ObjectiveFS environment for the command
        env = os.environ.copy()
        env["OBJECTIVEFS_ENV"] = env_dir
        command = "mount.objectivefs list -a"  # List all filesystems
        
        # Run the command and capture output
        output = subprocess.check_output(command, shell=True, env=env, stderr=subprocess.STDOUT)
        
        # Parse output to find if the name is already in use
        output_lines = output.decode("utf-8").splitlines()
        for line in output_lines:
            if line.startswith(filesystem_name + "\t"):  # Match exact filesystem name followed by a tab
                return False, f"Filesystem name '{filesystem_name}' is already in use."
                
        # If no match is found, the name is available
        return True, ""
    
    except subprocess.CalledProcessError as e:
        return False, f"Error checking filesystem availability: {e.output.decode('utf-8')}"

def create_filesystem(env_dir, bucket_name, filesystem_name):
    """
    Creates an ObjectiveFS filesystem using the specified name and environment directory.

    Parameters:
        env_dir (str): Directory containing the environment config files.
        bucket_name (str): Name of the S3 bucket where the filesystem will be created.
        filesystem_name (str): Desired name for the filesystem.

    Returns:
        bool: True if filesystem creation was successful, False otherwise.
    """
    try:
        # Validate filesystem name syntax
        valid_name, message = validate_filesystem_name(filesystem_name)
        if not valid_name:
            print(message)
            return False

        # Check if filesystem name is available
        available, message = check_name_availability(filesystem_name, env_dir)
        if not available:
            print(message)
            return False

        # Set up the environment and run the create command
        env = os.environ.copy()
        env["OBJECTIVEFS_ENV"] = env_dir
        command = f"sudo OBJECTIVEFS_ENV={env_dir} mount.objectivefs create {filesystem_name}"
        print("COMMAND is: ", command)

        # Run the command to create the filesystem
        output = subprocess.check_output(command, shell=True, env=env, stderr=subprocess.STDOUT)
        print(f"Filesystem '{filesystem_name}' created successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Failed to create filesystem: {e.output.decode('utf-8')}")
        return False
    except Exception as e:
        print(f"Error during filesystem creation: {e}")
        return False
