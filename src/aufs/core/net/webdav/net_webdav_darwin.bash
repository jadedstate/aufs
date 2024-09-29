#!/bin/bash

WEBDAV_SERVER="DATALOC"
MOUNT_POINT="MNTPOINT"
USERNAME="UNAME"
PASSWORD="PSSWD"  # Replace with the escaped version of your password

# Create mount point
mkdir -p $MOUNT_POINT

# Mount WebDAV share on macOS using mount_webdav
mount_webdav -S http://$USERNAME:$PASSWORD@$WEBDAV_SERVER $MOUNT_POINT

# Check if the mount was successful
if mount | grep -q $MOUNT_POINT; then
  echo "WebDAV share successfully mounted at $MOUNT_POINT."
else
  echo "Failed to mount WebDAV share."
  exit 1
fi
