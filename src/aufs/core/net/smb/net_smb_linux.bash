#!/bin/bash

# SMB_SERVER="192.168.0.10/Fjob"
SMB_SERVER="18.175.206.107/aufs-smb0"
MOUNT_POINT="MNTPOINT"
USERNAME="UNAME"
PASSWORD="PSSWD"  # Replace with the escaped version of your password

# Create mount point
# mkdir -p $MOUNT_POINT

# Mount the SMB share
mount -t cifs $SMB_SERVER $MOUNT_POINT -o username=$USERNAME,password=$PASSWORD,vers=3.0

# Check if the mount was successful
if mount | grep -q $MOUNT_POINT; then
    echo "SMB share successfully mounted at $MOUNT_POINT."
else
    echo "Failed to mount SMB share."
    exit 1
fi
