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

$WebDavServer = "DATALOC"
$MountPoint = "MNTPOINT"  # Drive letter or mount point selected dynamically
$Username = "UNAME"
$Password = "PSSWD"

# Convert the password to a secure string without ConvertTo-SecureString
$SecurePassword = Create-SecureString $Password

# Create the credential object
$Credential = New-Object System.Management.Automation.PSCredential ($Username, $SecurePassword)

# Map the WebDAV share to the specified drive letter or mount point
try {
    # Mounting WebDAV drive using net use
    net use $MountPoint $WebDavServer /user:$Username $Password /persistent:yes

    # Check if the mount was successful
    if (Test-Path "$($MountPoint):\") {
        Write-Host "WebDAV share successfully mounted at $MountPoint."
    } else {
        Write-Host "Failed to mount WebDAV share."
        exit 1
    }
} catch {
    Write-Host "Error: Failed to mount the WebDAV share: $_"
    exit 1
}
