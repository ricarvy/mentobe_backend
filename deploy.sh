#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

APP_NAME="mentobe-backend"
PORT=8901

echo "Building Docker image for $APP_NAME..."
docker build -t $APP_NAME .

echo "Checking for existing container..."
if [ "$(docker ps -aq -f name=$APP_NAME-container)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $APP_NAME-container || true
    docker rm $APP_NAME-container || true
fi

echo "Starting new container on port $PORT..."
docker run -d \
  --name $APP_NAME-container \
  -p 0.0.0.0:$PORT:8901 \
  --env-file .env \
  --restart unless-stopped \
  $APP_NAME

echo "Deployment complete!"
echo "Service is running on:"
echo "  - Local: http://localhost:$PORT"
echo "  - Network: http://<server-ip>:$PORT"
docker ps -f name=$APP_NAME-container
