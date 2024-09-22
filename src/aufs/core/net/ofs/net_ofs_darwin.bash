#!/bin/bash

# Define the bucket name and AWS credentials (these can be embedded or prompted for)
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
BUCKET_NAME="your-s3-bucket"

# Mount point for S3
MOUNT_POINT="/path/to/mount"

# Install Docker if it's not already installed
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Installing Docker..."
  sudo apt-get update && sudo apt-get install -y docker.io
fi

# Build or pull the ObjectiveFS Docker image (assuming the image is already on Docker Hub)
docker pull your-docker-repo/objectivefs-container

# Run the Docker container to mount the S3 bucket
docker run -d --privileged \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -v "$MOUNT_POINT:/mnt/s3" \
  your-docker-repo/objectivefs-container

echo "S3 bucket $BUCKET_NAME mounted at $MOUNT_POINT"
