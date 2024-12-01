import subprocess
import sys

def run_deadline_command(function_name, *args):
    """
    Wrapper to run any deadline_commands function as a subprocess.

    :param function_name: The name of the function to call.
    :param args: Arguments to pass to the function.
    """
    command = [sys.executable, '-m', 'src.rendering_utils.action.deadline_commands', function_name] + list(args)
    
    try:
        subprocess.run(command, check=True)
        print(f"{function_name} executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute {function_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deadline_wrapper.py <function_name> [arguments...]")
        sys.exit(1)
    
    function_name = sys.argv[1]
    args = sys.argv[2:]

    run_deadline_command(function_name, *args)
