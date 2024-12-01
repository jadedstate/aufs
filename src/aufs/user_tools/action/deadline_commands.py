import subprocess
import sys
import os
import re
import pandas as pd

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.fs_meta.parquet_tools import df_write_to_pq
from src.aufs.user_tools.fs_meta.files_paths import set_a_render_root_for_os

DEADLINE_COMMAND = "/opt/Thinkbox/Deadline10/bin/deadlinecommand"

def get_all_jobs_info():
    """
    Retrieves all jobs info from Deadline.
    """
    try:
        all_jobs_info = subprocess.check_output([DEADLINE_COMMAND, '-GetJobs', 'True']).decode('utf-8')
        return all_jobs_info
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving job information: {e}")
        return None

def parse_jobs_info(output):
    """
    Parses the jobs info output from Deadline into a list of dictionaries, each representing a job.
    
    :param output: The raw string output from the Deadline command.
    :return: A list of dictionaries, each representing a job's key-value pairs.
    """
    jobs = []
    current_job = {}
    job_id = None

    # Regex to match square-bracketed job IDs (e.g., [66bf5e6ec93eadde93a93999])
    job_id_pattern = re.compile(r'^\[(.+)\]$')

    for line in output.splitlines():
        line = line.strip()
        if not line:  # Skip empty lines
            continue

        job_id_match = job_id_pattern.match(line)
        if job_id_match:  # New job starts here
            if current_job and job_id:  # Save the previous job before starting a new one
                jobs.append(current_job)
            job_id = job_id_match.group(1)
            current_job = {'JobId': job_id}
        else:  # Process key=value lines
            if '=' in line:
                key, value = line.split('=', 1)
                current_job[key.strip()] = value.strip()

    if current_job and job_id:  # Add the last job if it exists
        jobs.append(current_job)
    
    return jobs

def count_queued_and_running_jobs():
    """
    Counts the number of queued and running jobs from the parsed Deadline job information.
    
    :return: A tuple with the number of queued jobs and running jobs.
    """
    raw_jobs_info = get_all_jobs_info()
    if raw_jobs_info is None:
        return 0, 0  # If there was an error getting job info, return 0 for both counts
    
    jobs = parse_jobs_info(raw_jobs_info)
    queued_count = 0
    running_count = 0
    
    for job in jobs:
        job_status = job.get("JobStatus", "").lower()
        if job_status == "queued":
            queued_count += 1
        elif job_status == "rendering":
            running_count += 1
    
    return queued_count, running_count

def save_jobs_to_parquet(jobs, output_path):
    """
    Saves the parsed job information into a Parquet file.
    
    :param jobs: A list of dictionaries, each representing a job's key-value pairs.
    :param output_path: The path where the Parquet file will be saved.
    """
    df = pd.DataFrame(jobs)
    df_write_to_pq(df, output_path)

def get_and_save_all_jobs_info(client, project, output_path=None):
    """
    Retrieves all jobs info from Deadline, parses it, and saves it to a Parquet file.
    
    :param client: The client name.
    :param project: The project name.
    :param output_path: Optional path where the Parquet file will be saved. If not provided, a default path will be used.
    """
    root = set_a_render_root_for_os('R:/')
    
    # Set up the file name and output path
    parquet_file = f"{client}-{project}_deadline_all_jobs.parquet"
    
    if output_path is None:
        # If output_path is not provided, construct the default path
        output_path = os.path.join(root, 'dsvfx/render/jobs', client, project, 'deadline')
        os.makedirs(output_path, exist_ok=True)
    else:
        # Ensure the provided output path exists
        os.makedirs(output_path, exist_ok=True)
    
    # Construct the absolute file path
    absolute_out = os.path.join(output_path, parquet_file)
    
    # Retrieve and parse jobs info
    raw_jobs_info = get_all_jobs_info()
    if raw_jobs_info is not None:
        jobs = parse_jobs_info(raw_jobs_info)
        
        # Save the jobs info to a Parquet file
        save_jobs_to_parquet(jobs, absolute_out)
        print(f"Jobs info saved to {absolute_out}")
    else:
        print("No jobs info retrieved.")

def generate_submission_info_files(job_id, output_directory=None):
    """
    Generates the submission info files for a given job ID.
    
    :param job_id: The ID of the Deadline job to generate submission info files for.
    :param output_directory: Optional directory where the files will be generated. If not provided, a temporary directory will be used.
    :return: A tuple containing the paths to the generated job info file and plugin info file.
    """
    if output_directory is None:
        output_directory = os.path.join(os.getcwd(), f"submission_files_{job_id}")
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Specify the paths for the job info and plugin info files
    job_info_file = os.path.join(output_directory, "job_info.job")
    plugin_info_file = os.path.join(output_directory, "plugin_info.job")
    
    command = [
        DEADLINE_COMMAND,
        "-GenerateSubmissionInfoFiles",  # Correct command flag
        job_id,
        job_info_file,
        plugin_info_file
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"Submission info files generated: {job_info_file}, {plugin_info_file}")
        print(result.stdout)  # Print the command's output for further debugging
        
        if os.path.exists(job_info_file) and os.path.exists(plugin_info_file):
            return job_info_file, plugin_info_file
        else:
            raise FileNotFoundError("Failed to generate submission info files.")
    
    except subprocess.CalledProcessError as e:
        print(f"Error generating submission info files: {e.stderr}")
        print(f"Command: {' '.join(command)}")
        return None, None

def get_job_info(job_id):
    """
    Retrieves the job info and plugin info from Deadline using the job ID.
    """
    try:
        job_info = subprocess.check_output([DEADLINE_COMMAND, '-GetJob', job_id, 'JobInfo']).decode('utf-8')
        plugin_info = subprocess.check_output([DEADLINE_COMMAND, 'GetJob', job_id, 'PluginInfo']).decode('utf-8')
        return job_info, plugin_info
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving job information: {e}")
        return None, None

def submit_background_job(job_info_file, plugin_info_file, deadline_command=DEADLINE_COMMAND):
    """
    Submits a job to Deadline in the background using the provided job_info and plugin_info files.
    
    :param job_info_file: Path to the job info file.
    :param plugin_info_file: Path to the plugin info file.
    :param deadline_command: The path to the deadlinecommand executable.
    :return: The output from the submission command or an error message.
    """
    command = [
        deadline_command,
        "-SubmitBackgroundJob",
        job_info_file,
        plugin_info_file
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"Background job submitted successfully: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to submit background job: {e.stderr}")
        return None

def get_job_tasks(job_id):
    command = [DEADLINE_COMMAND, "-GetJobTasks", job_id]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting job tasks: {result.stderr}")
        return None
    return parse_job_tasks_output(result.stdout)

def parse_job_tasks_output(output):
    tasks = []
    task = {}
    for line in output.splitlines():
        if line.strip() == "":
            if task:
                tasks.append(task)
                task = {}
        else:
            key, value = line.split('=', 1)
            task[key.strip()] = value.strip()
    if task:
        tasks.append(task)
    return tasks

def complete_tasks(job_id, task_ids):
    command = [DEADLINE_COMMAND, "-CompleteJobTasks", job_id] + task_ids
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error completing tasks: {result.stderr}")
    return result.stdout

def fail_tasks(job_id, task_ids):
    command = [DEADLINE_COMMAND, "-FailJobTasks", job_id] + task_ids
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error failing tasks: {result.stderr}")
    return result.stdout

def requeue_tasks(job_id, task_ids):
    task_id_list = ",".join(task_ids)  # Join the task IDs into a comma-separated string
    command = [DEADLINE_COMMAND, "-RequeueJobTasks", job_id, task_id_list]
    print("Subprocessing the following deadlinecommand: ")
    print(command)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error requeuing tasks: {result.stderr}")
    return result.stdout

def suspend_tasks(job_id, task_ids):
    command = [DEADLINE_COMMAND, "-SuspendJobTasks", job_id] + task_ids
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error suspending tasks: {result.stderr}")
    return result.stdout

def resume_tasks(job_id, task_ids):
    task_id_list = ",".join(task_ids)  # Join the task IDs into a comma-separated string
    command = [DEADLINE_COMMAND, "-ResumeJobTasks", job_id, task_id_list]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error resuming tasks: {result.stderr}")
    return result.stdout


# (All your existing functions here)

def main():
    """
    Main function to parse arguments and call the appropriate Deadline command function.
    """
    if len(sys.argv) < 2:
        print("Usage: python deadline_commands.py <function_name> [arguments...]")
        sys.exit(1)

    function_name = sys.argv[1]
    args = sys.argv[2:]

    if function_name == "get_and_save_all_jobs_info":
        if len(args) < 2:
            print("Usage: python deadline_commands.py get_and_save_all_jobs_info <client> <project> [output_path]")
            sys.exit(1)
        client = args[0]
        project = args[1]
        output_path = args[2] if len(args) > 2 else None
        get_and_save_all_jobs_info(client, project, output_path)
    
    elif function_name == "generate_submission_info_files":
        if len(args) < 1:
            print("Usage: python deadline_commands.py generate_submission_info_files <job_id> [output_directory]")
            sys.exit(1)
        job_id = args[0]
        output_directory = args[1] if len(args) > 1 else None
        generate_submission_info_files(job_id, output_directory)

    elif function_name == "get_job_info":
        if len(args) < 1:
            print("Usage: python deadline_commands.py get_job_info <job_id>")
            sys.exit(1)
        job_id = args[0]
        job_info, plugin_info = get_job_info(job_id)
        print("Job Info:", job_info)
        print("Plugin Info:", plugin_info)
    
    elif function_name == "submit_background_job":
        if len(args) < 2:
            print("Usage: python deadline_commands.py submit_background_job <job_info_file> <plugin_info_file>")
            sys.exit(1)
        job_info_file = args[0]
        plugin_info_file = args[1]
        submit_background_job(job_info_file, plugin_info_file)
    
    elif function_name == "get_job_tasks":
        if len(args) < 1:
            print("Usage: python deadline_commands.py get_job_tasks <job_id>")
            sys.exit(1)
        job_id = args[0]
        tasks = get_job_tasks(job_id)
        print("Tasks:", tasks)
    
    elif function_name == "complete_tasks":
        if len(args) < 2:
            print("Usage: python deadline_commands.py complete_tasks <job_id> <task_ids...>")
            sys.exit(1)
        job_id = args[0]
        task_ids = args[1:]
        complete_tasks(job_id, task_ids)
    
    elif function_name == "fail_tasks":
        if len(args) < 2:
            print("Usage: python deadline_commands.py fail_tasks <job_id> <task_ids...>")
            sys.exit(1)
        job_id = args[0]
        task_ids = args[1:]
        fail_tasks(job_id, task_ids)
    
    elif function_name == "requeue_tasks":
        if len(args) < 2:
            print("Usage: python deadline_commands.py requeue_tasks <job_id> <task_ids...>")
            sys.exit(1)
        job_id = args[0]
        task_ids = args[1:]
        requeue_tasks(job_id, task_ids)
    
    elif function_name == "suspend_tasks":
        if len(args) < 2:
            print("Usage: python deadline_commands.py suspend_tasks <job_id> <task_ids...>")
            sys.exit(1)
        job_id = args[0]
        task_ids = args[1:]
        suspend_tasks(job_id, task_ids)
    
    elif function_name == "resume_tasks":
        if len(args) < 2:
            print("Usage: python deadline_commands.py resume_tasks <job_id> <task_ids...>")
            sys.exit(1)
        job_id = args[0]
        task_ids = args[1:]
        resume_tasks(job_id, task_ids)
    
    else:
        print(f"Unknown function: {function_name}")
        sys.exit(1)

if __name__ == "__main__":
    main()
