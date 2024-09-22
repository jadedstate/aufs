# Check for WSL installation
if (-not (Get-WindowsFeature -Name Microsoft-Windows-Subsystem-Linux).InstallState -eq 'Installed') {
    Write-Host "WSL is not installed."
    $confirmRestart = Read-Host "WSL needs to be installed, and the system will need to restart. Do you want to proceed? (Y/N)"
    
    if ($confirmRestart -eq 'Y' -or $confirmRestart -eq 'y') {
        Write-Host "Installing WSL..."
        wsl --install
        Write-Host "Restarting the system..."
        Restart-Computer -Force
    } else {
        Write-Host "Installation aborted. WSL is required to proceed."
        exit 1
    }
} else {
    Write-Host "WSL is already installed."
}

# Check for Docker Desktop installation
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop not installed. Installing Docker Desktop..."
    $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
    Invoke-WebRequest -Uri https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe -OutFile $dockerInstaller
    Start-Process -FilePath $dockerInstaller -Wait
    Remove-Item $dockerInstaller
} else {
    Write-Host "Docker Desktop is already installed."
}

# Define the local path for the ObjectiveFS Docker image
$LocalImagePath = "G:/aufs/ofs/docker/ofs_dl_london-container.tar"

# Load the ObjectiveFS container if it's not already loaded
$ContainerName = "objectivefs-container"
if (-not (docker images -q $ContainerName)) {
    Write-Host "Loading ObjectiveFS container from local path..."
    docker load -i $LocalImagePath
} else {
    Write-Host "ObjectiveFS container is already loaded."
}

# Set the mount point to any empty directory
$MountPoint = "G:/aufs/mount/ofs_dl_london"  # Ensure this is an empty directory

# Check if the directory exists and is empty
if (-not (Test-Path $MountPoint)) {
    Write-Host "Creating mount directory..."
    New-Item -Path $MountPoint -ItemType Directory
} elseif ((Get-ChildItem $MountPoint).Count -gt 0) {
    Write-Host "Error: Mount directory is not empty. Please choose an empty directory."
    exit 1
}

# Run the Docker container, mounting to the empty directory
docker run -d --privileged `
  -v "$($MountPoint):/mnt/deadline-london" `
  objectivefs-container

Write-Host "ObjectiveFS mounted at $MountPoint"
