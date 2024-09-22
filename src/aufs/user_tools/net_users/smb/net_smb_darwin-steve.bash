#!/bin/bash

SMB_SERVER="\\18.175.206.107\sm_data"
MOUNT_POINT="MNTPOINT"
USERNAME="steve"
PASSWORD="tinker458sincin"  # Replace with the escaped version of your password

# Create mount point
mkdir -p $MOUNT_POINT

# Mount SMB share on macOS
mount_smbfs smb://$USERNAME:$PASSWORD@$SMB_SERVER $MOUNT_POINT

if mount | grep -q $MOUNT_POINT; then
  echo "SMB share successfully mounted at $MOUNT_POINT."
else
  echo "Failed to mount SMB share."
  exit 1
fi
