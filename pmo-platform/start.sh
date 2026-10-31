#!/bin/bash
# =============================================================
# PMO 运维管理平台 - 一键启动脚本
# 适用于个人 PC 部署（Linux / macOS / Windows Git Bash）
# 默认使用 SQLite 零配置数据库
# =============================================================

set -e

cd "$(dirname "$0")"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  PMO 运维管理平台 - 启动${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}未找到 python3，请先安装 Python 3.11+${NC}"
    exit 1
fi

# 检查 Node
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}未找到 node，请先安装 Node.js 18+${NC}"
    exit 1
fi

PORT=${PORT:-8000}

# 安装后端依赖
echo -e "${GREEN}[1/4] 检查后端依赖...${NC}"
if [ ! -d "pmo-server/.venv" ]; then
    echo "  创建虚拟环境..."
    cd pmo-server
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt -q
    cd ..
else
    source pmo-server/.venv/bin/activate
fi

# 构建前端
echo -e "${GREEN}[2/4] 构建前端...${NC}"
if [ ! -d "pmo-web/dist" ] || [ "$1" = "--rebuild" ]; then
    cd pmo-web
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    cd ..
fi

# 启动后端（同时托管前端静态文件）
echo -e "${GREEN}[3/4] 启动服务...${NC}"
echo -e "  端口: ${PORT}"
echo -e "  数据库: SQLite (pmo-server/pmo.db)"

# 杀掉旧进程
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1

cd pmo-server
python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &
SERVER_PID=$!
cd ..

# 等待启动
sleep 4
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}[4/4] 启动成功！${NC}"
    echo ""
    echo -e "  访问地址: ${BLUE}http://localhost:${PORT}${NC}"
    echo -e "  默认账号: ${YELLOW}admin / admin123${NC}"
    echo ""
    echo -e "  按 Ctrl+C 停止服务"
    wait $SERVER_PID
else
    echo -e "${YELLOW}服务启动失败，请查看日志${NC}"
    exit 1
fi
