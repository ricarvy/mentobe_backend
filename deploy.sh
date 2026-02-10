#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

APP_NAME="mentobe-backend"
CONTAINER_NAME="$APP_NAME-container"
PORT=8901

# 0. Pull latest code
# 从远程仓库拉取最新代码
echo "Pulling latest code..."
git pull origin master

# 1. Build the Docker image
# 使用当前目录下的 Dockerfile 构建镜像
echo "Building Docker image for $APP_NAME..."
docker build -t $APP_NAME .

# 2. Check for existing container and cleanup
# 检查端口占用
echo "Checking if port $PORT is occupied..."
if [ "$(docker ps -q --filter "publish=$PORT")" ]; then
    echo "Port $PORT is occupied. Removing container..."
    docker rm -f $(docker ps -q --filter "publish=$PORT")
fi

# 检查是否存在同名容器，如果存在则停止并删除，确保环境纯净
echo "Checking for existing container: $CONTAINER_NAME..."
if [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "Found existing container: $CONTAINER_NAME"
    
    echo "Removing container..."
    docker rm -f $CONTAINER_NAME || true
    
    echo "Existing container removed."
else
    echo "No existing container found."
fi

# 3. Start new container
# 启动新容器，映射端口，并加载环境变量
echo "Starting new container on port $PORT..."
# --name: 指定容器名称
# -p: 端口映射 (宿主机端口:容器端口)
# --env-file: 从 .env.prod 文件加载环境变量
# --restart: 容器退出时的重启策略
docker run -d \
  --name $CONTAINER_NAME \
  -p 0.0.0.0:$PORT:8901 \
  --env-file .env.prod \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  $APP_NAME

echo "Deployment complete!"
echo "Service is running on:"
echo "  - Local: http://localhost:$PORT"
echo "  - Network: http://<server-ip>:$PORT"
docker ps -f name=$APP_NAME-container
