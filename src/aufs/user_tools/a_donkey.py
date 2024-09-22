import os
import subprocess
import sys
import time

def check_docker_installed():
    """Check if Docker is installed."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("Docker is installed.")
    except subprocess.CalledProcessError:
        print("Docker is not installed or not found in PATH.")
        sys.exit(1)

def ensure_docker_running():
    """Check if Docker is running by verifying the service status."""
    try:
        docker_status = subprocess.run(["docker", "info"], check=True, capture_output=True)
        print("Docker is running.")
    except subprocess.CalledProcessError:
        print("Docker Desktop is not running. Please start Docker Desktop.")
        sys.exit(1)

def load_docker_image(local_image_path, container_name):
    """Check if the Docker image is already loaded. If not, load it."""
    try:
        result = subprocess.run(["docker", "images", "-q", container_name], capture_output=True, text=True)
        if not result.stdout.strip():
            print(f"Loading Docker image from {local_image_path}...")
            subprocess.run(["docker", "load", "-i", local_image_path], check=True)
            print("Docker image loaded successfully.")
        else:
            print("Docker image is already loaded.")
    except subprocess.CalledProcessError as e:
        print(f"Error loading Docker image: {e}")
        sys.exit(1)

def run_docker_container(mount_point, container_name):
    """Run the Docker container with the specified mount point and ensure the bind is successful."""
    try:
        # Convert backslashes to forward slashes for Docker compatibility
        mount_point = mount_point.replace("\\", "/")
        
        # Build and execute the Docker run command
        docker_command = [
            "docker", "run", "-d", "--network", "host",  # Use host network mode
            "--privileged",
            "-v", f"{mount_point}:/mnt/deadline-london",  # Mount point for ObjectiveFS
            "-v", "G:/aufs/persistent_cache:/mnt/ofs_cache",  # Persistent cache directory
            container_name
        ]

        print(f"Running Docker command: {' '.join(docker_command)}")
        result = subprocess.run(docker_command, check=True, capture_output=True, text=True)
        container_id = result.stdout.strip()
        print(f"Docker container started with ID: {container_id}")

        # Check that the mount point is shared inside the container
        check_mount_command = [
            "docker", "exec", container_id, "ls", "/mnt/deadline-london"
        ]
        print(f"Checking bind mount inside container: {container_id}")
        mount_result = subprocess.run(check_mount_command, capture_output=True, text=True)
        
        if mount_result.returncode != 0:
            print("Error: Bind mount not available in the container. Please check the mount point.")
            sys.exit(1)
        else:
            print(f"Bind mount is available: {mount_result.stdout.strip()}")

        # After verifying the bind mount, run mount -a inside the container
        mount_command = ["docker", "exec", container_id, "mount", "-a"]
        print(f"Running 'mount -a' inside the container: {container_id}")
        subprocess.run(mount_command, check=True)
        print("ObjectiveFS filesystem mounted successfully.")
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to start Docker container or mount filesystem: {e}")
        sys.exit(1)

def main():
    # Simulate user input for Docker image and mount point
    local_image_path = "G:/aufs/ofs/docker/ofs_dl_london-smb-container.tar"
    container_name = "objectivefs-smb-container"
    mount_point = input("Enter the path for the mount point (e.g., G:/aufs/mount/ofs_dl_london): ")

    # Check if Docker is installed and running
    check_docker_installed()
    ensure_docker_running()

    # Load Docker image if not already loaded
    load_docker_image(local_image_path, container_name)

    # Run the Docker container with the specified mount point
    run_docker_container(mount_point, container_name)

if __name__ == "__main__":
    main()
