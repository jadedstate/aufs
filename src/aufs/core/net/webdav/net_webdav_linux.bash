#!/bin/bash

WEBDAV_SERVER="DATALOC"
MOUNT_POINT="MNTPOINT"
USERNAME="UNAME"
PASSWORD="PSSWD"  # Replace with the escaped version of your password

# Create mount point
mkdir -p $MOUNT_POINT

# Mount the WebDAV share on Linux using davfs2
echo "$USERNAME $PASSWORD" > ~/.davfs2/secrets
chmod 600 ~/.davfs2/secrets

mount -t davfs http://$WEBDAV_SERVER $MOUNT_POINT -o uid=1000,gid=1000

# Check if the mount was successful
if mount | grep -q $MOUNT_POINT; then
    echo "WebDAV share successfully mounted at $MOUNT_POINT."
else
    echo "Failed to mount WebDAV share."
    exit 1
fi
