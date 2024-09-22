# Define variables
$rcloneUrl = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
$winFspUrl = "https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi"
$mountDrive = "X:"
$s3Bucket = "bucketname"  # Replace with your actual S3 bucket name
$s3Remote = "s3remote"  # Name for the remote configuration in Rclone
$rcloneConfigPath = "$env:APPDATA\rclone\rclone.conf"

# Step 1: Download and Install Rclone
Write-Host "Downloading Rclone..."
$zipPath = "$env:TEMP\rclone.zip"
Invoke-WebRequest -Uri $rcloneUrl -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath "C:\rclone" -Force
Remove-Item -Path $zipPath

# Step 2: Download and Install WinFsp
Write-Host "Downloading and Installing WinFsp..."
$winFspInstaller = "$env:TEMP\winfsp.msi"
Invoke-WebRequest -Uri $winFspUrl -OutFile $winFspInstaller
Start-Process -FilePath msiexec.exe -ArgumentList "/i $winFspInstaller /quiet" -Wait
Remove-Item -Path $winFspInstaller

# Step 3: Add Rclone to PATH (if necessary)
$env:Path += ";C:\rclone\rclone.exe"

# Set variables
$rcloneConfigPath = "C:\rclone\rclone.conf"
$s3Remote = "your-s3-remote"  # Replace with your S3 remote name
$s3Bucket = "your-s3-bucket"  # Replace with your S3 bucket name
$mountDrive = "X:"  # Replace with the drive letter where you want to mount the bucket

# Set the correct path to rclone.exe
$rcloneExePath = "C:\rclone\rclone-v1.68.0-windows-amd64\rclone.exe"

# Step 4: Configure Rclone for S3 if the config file doesn't exist
if (-Not (Test-Path $rcloneConfigPath)) {
    Write-Host "Configuring Rclone for S3..."

    # Use Start-Process to call rclone with arguments as strings
    $arguments = @(
        'config', 'create', $s3Remote, 's3',
        'provider', 'AWS',
        'access_key_id', 'your-access-key',  # Replace with actual access key
        'secret_access_key', 'your-secret-key',  # Replace with actual secret key
        'region', 'us-west-1',  # Replace with your desired region
        '--config', $rcloneConfigPath
    )

    Start-Process $rcloneExePath -ArgumentList $arguments -NoNewWindow -Wait
}

# Step 5: Mount the S3 bucket using Rclone
Write-Host "Mounting S3 bucket..."

# Prepare arguments for rclone mount
$mountArguments = @(
    'mount',
    "$($s3Remote):$($s3Bucket)",  # Escape the colon correctly
    $mountDrive,
    '--vfs-cache-mode', 'full',
    '--config', $rcloneConfigPath
)

Start-Process -FilePath $rcloneExePath -ArgumentList $mountArguments -NoNewWindow -Wait

Write-Host "S3 bucket mounted at drive $mountDrive."

# Optionally, check if the mount was successful
if (Test-Path "$mountDrive\") {
    Write-Host "Mount successful. You can access the S3 bucket at $mountDrive."
} else {
    Write-Host "Mount failed. Please check the configuration."
}

# Step 6: Unmount the drive (optional, if you want to clean up)
# To unmount the drive, you can use this:
# & "C:\rclone\rclone.exe" unmount $mountDrive
