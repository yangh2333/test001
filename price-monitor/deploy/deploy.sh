#!/bin/bash
set -e

echo "========================================="
echo "  价格监控系统 - 阿里云ECS一键部署脚本"
echo "========================================="

# 配置变量
APP_DIR="/opt/price-monitor"
APP_USER="www-data"
PORT=8080

# 1. 安装系统依赖
echo "[1/7] 安装系统依赖..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx supervisor

# 2. 创建应用目录
echo "[2/7] 创建应用目录..."
mkdir -p $APP_DIR/{data,logs,templates}
mkdir -p $APP_DIR/deploy
chown -R $APP_USER:$APP_USER $APP_DIR

# 3. 创建Python虚拟环境
echo "[3/7] 创建Python虚拟环境..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. 配置应用文件
echo "[4/7] 配置应用文件..."
if [ ! -f "$APP_DIR/config.json" ]; then
    cp /tmp/config.json $APP_DIR/config.json 2>/dev/null || true
fi

if [ ! -f "$APP_DIR/schema.sql" ]; then
    cp /tmp/schema.sql $APP_DIR/schema.sql 2>/dev/null || true
fi

# 5. 初始化数据库
echo "[5/7] 初始化数据库..."
source venv/bin/activate
python3 -c "import sys; sys.path.insert(0, '$APP_DIR'); from monitor import init_database; init_database()"

# 6. 配置systemd服务
echo "[6/7] 配置systemd服务..."
cp $APP_DIR/deploy/price-monitor.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable price-monitor
systemctl start price-monitor

# 7. 配置Nginx
echo "[7/7] 配置Nginx..."
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/price-monitor
ln -sf /etc/nginx/sites-available/price-monitor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "访问地址: http://<您的公网IP>/"
echo "健康检查: http://<您的公网IP>/health"
echo ""
echo "常用命令:"
echo "  systemctl status price-monitor  # 查看服务状态"
echo "  systemctl restart price-monitor # 重启服务"
echo "  journalctl -u price-monitor -f # 查看日志"
echo ""
