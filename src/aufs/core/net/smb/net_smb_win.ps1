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

$SMBServer = "\\18.175.206.107\nh_data"
$MountPoint = "Z"  # Drive letter or mount point selected dynamically
$Username = "neil"
$Password = "am4ih7qnllar2du0eqvj8utv"

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
