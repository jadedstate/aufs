# lib/config.py

import platform
import os
import sys
import subprocess

import pandas as pd

class loadConfigs:
    def __init__(self):
        self.root = F_root_path()
        self.all_jobs_parquets = f'{self.root}/fs_main/parquet/all_jobs/'

        self.alljob_configs = f'{self.all_jobs_parquets}/alljob_configs.parquet'
        self.alljobs_allshot_configs = f'{self.all_jobs_parquets}/alljobs_allshot_configs.parquet'
        self.thumb_defaults = f'{self.all_jobs_parquets}/alljobs_thumb_defaults.parquet'

    def load_alljob_configs(self):
        
        return pd.read_parquet(self.alljob_configs)

    def load_alljobs_allshot_configs(self):
        
        return pd.read_parquet(self.alljobs_allshot_configs)
    
    def load_thumb_defaults(self):
        
        return pd.read_parquet(self.thumb_defaults)
    
def F_root_path(all=False):
    paths = {
        'Windows': 'F:/',
        'Linux': '/mnt/localF/',
        'Darwin': '/Volumes/localF/'
    }
    if all:
        return paths
    else:
        return paths.get(platform.system(), "Unsupported operating system")

def launch_script_in_venv(script_name, script_dir=None, additional_args=None):
    """
    Launches a script using the Python executable from the current virtual environment.

    :param script_name: Name of the script to launch.
    :param script_dir: Directory where the script is located. If None, uses the current directory.
    :param additional_args: List of additional arguments to pass to the script.
    :return: Popen object for the launched process.
    """
    if script_dir is None:
        script_dir = os.path.dirname(__file__)
    
    # Get the path to the Python executable in the virtual environment
    venv_python = os.path.join(sys.prefix, 'bin', 'python' if os.name != 'nt' else 'Scripts\\python.exe')

    # Construct the path to the script
    script_path = os.path.join(script_dir, script_name)

    # Create the command to launch the script
    command = [venv_python, script_path]

    # Add additional arguments if provided
    if additional_args:
        command.extend(additional_args)

    # Use the subprocess module to launch the script
    return subprocess.Popen(command, start_new_session=True)

def set_root_path(all=False):
    # have this get the root from a config somehow
    if platform.system() == 'Windows':
        return 'F:'
    elif platform.system() == 'Linux':
        return '/mnt/localF'
    elif platform.system() == 'Darwin':
        return '/Volumes/localF'
    else:
        raise EnvironmentError("Unsupported operating system")

def set_env_vars(widget, env):
    """
    Set environment variables from the env dictionary as attributes on the widget.

    Args:
        widget: The widget (or any object) where the environment variables will be set.
        env (dict): Dictionary of environment variables to set as attributes.
    """
    for key, value in env.items():
        setattr(widget, key, value)