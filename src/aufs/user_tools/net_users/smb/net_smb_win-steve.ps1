# Function to create a secure string without using ConvertTo-SecureString
function Create-SecureString {
    param (
        [string]$PlainTextPassword
    )
    # .NET-based secure string conversion without requiring Microsoft.PowerShell.Security
    $SecurePassword = New-Object -TypeName System.Security.SecureString
    $PlainTextPassword.ToCharArray() | ForEach-Object { $SecurePassword.AppendChar($_) }
    return $SecurePassword
}

$SMBServer = "\\18.175.206.107\sm_data"
$MountPoint = "MNTPOINT"  # Drive letter or mount point selected dynamically
$Username = "steve"
$Password = "tinker458sincin"

# Convert the password to a secure string without ConvertTo-SecureString
$SecurePassword = Create-SecureString $Password

# Create the credential object
$Credential = New-Object System.Management.Automation.PSCredential ($Username, $SecurePassword)

# Mount the network drive using the specified mount point (e.g., a drive letter)
try {
    New-PSDrive -Name $MountPoint -PSProvider FileSystem -Root $SMBServer -Credential $Credential -Persist -ErrorAction Stop

    # Check if the mount was successful
    if (Test-Path "$($MountPoint):\") {
        Write-Host "SMB share successfully mounted at $MountPoint."
    } else {
        Write-Host "Failed to mount SMB share."
        exit 1
    }
} catch {
    Write-Host "Error: Failed to mount the SMB share: $_"
    exit 1
}
