# 价格监控系统 - 阿里云ECS部署指南

## 环境要求

- 阿里云ECS实例 (推荐 Ubuntu 20.04+ 或 CentOS 7+)
- Python 3.8+
- Nginx
- systemd

## 目录结构

```
/opt/price-monitor/
├── app.py              # Flask应用主程序
├── monitor.py          # 命令行程序
├── scrapers.py         # 价格抓取模块
├── config.json         # 配置文件
├── schema.sql         # 数据库初始化脚本
├── requirements.txt   # Python依赖
├── templates/         # Web页面模板
├── data/              # 数据库文件
├── logs/              # 日志文件
└── deploy/            # 部署配置文件
    ├── deploy.sh           # 一键部署脚本
    ├── price-monitor.service # systemd服务文件
    ├── nginx.conf          # Nginx配置
    └── security-group.md   # 安全组配置说明
```

## 部署步骤

### 方式一：手动部署

#### 1. 连接服务器

```bash
ssh root@<您的公网IP>
```

#### 2. 安装系统依赖

**Ubuntu/Debian:**
```bash
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx systemctl
```

**CentOS:**
```bash
yum install -y python3 python3-pip nginx systemctl
```

#### 3. 创建应用目录和用户

```bash
mkdir -p /opt/price-monitor/{data,logs,templates}
useradd -r -s /bin/false www-data || true
chown -R www-data:www-data /opt/price-monitor
```

#### 4. 上传应用代码

**方式A: 使用scp上传**
```bash
# 在本地执行
scp -r price-monitor/* root@<您的公网IP>:/opt/price-monitor/
```

**方式B: 使用Git**
```bash
cd /opt/price-monitor
git clone <您的仓库地址> .
```

#### 5. 创建Python虚拟环境并安装依赖

```bash
cd /opt/price-monitor
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. 配置应用

编辑 `config.json` 配置SMTP邮件服务：

```bash
vi /opt/price-monitor/config.json
```

```json
{
    "smtp": {
        "server": "smtp.qq.com",
        "port": 587,
        "username": "your_email@qq.com",
        "password": "your_auth_code",
        "from_address": "your_email@qq.com",
        "to_addresses": ["admin@example.com"],
        "use_tls": true
    }
}
```

#### 7. 初始化数据库

```bash
source venv/bin/activate
python3 monitor.py init
```

#### 8. 配置systemd服务

```bash
cp /opt/price-monitor/deploy/price-monitor.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable price-monitor
systemctl start price-monitor
```

#### 9. 配置Nginx

```bash
cp /opt/price-monitor/deploy/nginx.conf /etc/nginx/sites-available/price-monitor
ln -sf /etc/nginx/sites-available/price-monitor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

#### 10. 配置阿里云安全组

1. 登录阿里云ECS控制台
2. 选择目标实例 → 安全组 → 配置规则
3. 添加入方向规则：
   - 协议：TCP
   - 端口：80
   - 授权对象：0.0.0.0/0

详细说明见 [security-group.md](deploy/security-group.md)

### 方式二：使用一键部署脚本

#### 1. 上传代码到服务器

```bash
scp -r price-monitor/* root@<您的公网IP>:/tmp/
```

#### 2. 执行部署脚本

```bash
ssh root@<您的公网IP>
cd /tmp/price-monitor
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

## 验证部署

### 检查服务状态

```bash
# 检查应用服务
systemctl status price-monitor

# 检查Nginx服务
systemctl status nginx

# 检查端口监听
netstat -tlnp | grep -E '80|8080'
```

### 测试访问

```bash
# 本地测试
curl http://localhost/health

# 公网测试
curl http://<您的公网IP>/health
```

### 查看日志

```bash
# 应用日志
tail -f /opt/price-monitor/logs/access.log
tail -f /opt/price-monitor/logs/error.log

# systemd日志
journalctl -u price-monitor -f
```

## 访问应用

部署成功后，访问以下地址：

- **主界面**: http://<您的公网IP>/
- **健康检查**: http://<您的公网IP>/health
- **API接口**: http://<您的公网IP>/api/prices

## 常用运维命令

```bash
# 重启服务
systemctl restart price-monitor

# 停止服务
systemctl stop price-monitor

# 查看服务状态
systemctl status price-monitor

# 查看应用日志
journalctl -u price-monitor -n 100

# 重新加载配置
systemctl reload price-monitor

# 检查Nginx配置
nginx -t

# 重启Nginx
systemctl reload nginx
```

## 配置HTTPS（可选）

### 使用Let's Encrypt免费证书

```bash
# 安装certbot
apt-get install -y certbot python3-certbot-nginx

# 获取证书（需要域名）
certbot --nginx -d yourdomain.com

# 自动续期
certbot renew --dry-run
```

### 修改Nginx配置支持HTTPS

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 故障排查

### 1. 服务启动失败

```bash
# 查看详细错误
journalctl -u price-monitor -xe

# 手动测试运行
cd /opt/price-monitor
source venv/bin/activate
python3 app.py --port 8080
```

### 2. 端口被占用

```bash
# 查找占用端口的进程
netstat -tlnp | grep 8080
lsof -i :8080

# 杀死进程
kill -9 <PID>
```

### 3. 权限问题

```bash
chown -R www-data:www-data /opt/price-monitor
chmod -R 755 /opt/price-monitor
```

### 4. 数据库锁定

```bash
rm -f /opt/price-monitor/data/*.db-journal
systemctl restart price-monitor
```

### 5. Nginx 502错误

```bash
# 检查应用是否运行
curl http://127.0.0.1:8080/health

# 检查Nginx错误日志
tail -f /var/log/nginx/error.log
```

## 定时任务配置

建议设置每日自动扫描任务：

```bash
crontab -e
```

添加以下内容：

```
# 每天凌晨2点自动扫描价格
0 2 * * * cd /opt/price-monitor && /opt/price-monitor/venv/bin/python monitor.py scrape --auto >> /opt/price-monitor/logs/scrape.log 2>&1

# 每天凌晨3点生成报告
0 3 * * * cd /opt/price-monitor && /opt/price-monitor/venv/bin/python monitor.py report >> /opt/price-monitor/logs/report.log 2>&1
```

## 数据备份

```bash
# 备份数据库
cp /opt/price-monitor/data/price_monitor.db /opt/price-monitor/data/backup_$(date +%Y%m%d).db

# 设置定时备份（每天凌晨）
0 4 * * * cp /opt/price-monitor/data/price_monitor.db /opt/price-monitor/data/backup_$(date +\%Y\%m\%d).db
```

## 版本升级

```bash
cd /opt/price-monitor
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart price-monitor
```