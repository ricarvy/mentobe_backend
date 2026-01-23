#!/bin/bash

# ============================================
# Mentob AI - 后端海外 Docker 部署脚本
# ============================================
# 使用环境变量: .env.oversea.prod
# 部署端口: 8901
# ============================================

set -e

# 拉取最新代码
echo "正在拉取最新代码..."
git pull

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
CONTAINER_NAME="mentobe-backend-oversea"
IMAGE_NAME="mentobe-backend:oversea"
PORT=8901
ENV_FILE=".env.oversea.prod"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker
if ! command -v docker &> /dev/null; then
    print_error "未安装 Docker。"
    exit 1
fi

# 检查环境变量文件
if [ ! -f "$ENV_FILE" ]; then
    print_error "找不到环境变量文件 $ENV_FILE！"
    echo "请创建 $ENV_FILE 并配置必要的环境信息。"
    exit 1
fi

# 构建镜像
print_info "正在构建 Docker 镜像..."
docker build -t "$IMAGE_NAME" .

# 停止并删除旧容器
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    print_info "正在停止并删除现有容器..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# 运行容器
print_info "正在启动新容器..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:$PORT" \
  --restart unless-stopped \
  --env-file "$ENV_FILE" \
  "$IMAGE_NAME"

# 检查状态
sleep 2
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    print_success "后端服务部署成功！端口: $PORT"
    docker logs --tail 10 "$CONTAINER_NAME"
else
    print_error "部署失败。容器未运行。"
    docker logs --tail 20 "$CONTAINER_NAME"
    exit 1
fi
