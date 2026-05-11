# 价格监控系统 v1.2

## 项目简介

价格监控系统用于监控数据中心核心部件的市场价格变化，支持28项监控项目，涵盖8大品类。系统支持价格录入、自动价格扫描、预警检测、报告生成等功能，并提供直观的Web前端界面。

## 技术栈

- Python 3.6+
- SQLite 数据库
- Flask（Web框架）
- Gunicorn（WSGI服务器）
- Nginx（反向代理）
- requests/beautifulsoup4（网页抓取）
- openpyxl（Excel导出）

## 快速开始

### 本地开发

```bash
pip install -r requirements.txt
python app.py --port 8080
```

访问 http://localhost:8080

### 阿里云ECS部署

详细部署指南请查看 [DEPLOY.md](DEPLOY.md)

```bash
# 1. 上传代码到服务器
scp -r price-monitor/* root@<公网IP>:/opt/price-monitor/

# 2. 执行部署脚本
ssh root@<公网IP>
cd /opt/price-monitor
chmod +x deploy/deploy.sh
./deploy/deploy.sh

# 3. 配置阿里云安全组（开放80端口）
# 登录阿里云控制台 → ECS → 安全组 → 添加入方向规则：TCP 80
```

访问 http://<您的公网IP>/

## Web界面功能

### 监控概览
- 展示所有监控项目的当前价格和状态
- 统计监控项目总数、预警数量、正常项目数量
- 支持查看每个项目的价格历史
- 支持跳转到电商平台搜索页面

### 预警管理
- 显示所有未处理的预警信息
- 支持一键标记预警为已处理
- 预警信息包含触发时间和详细描述

### 自动扫描
- 选择单个或全部监控项目进行扫描
- 自动访问京东、阿里巴巴、淘宝等平台获取实时价格
- 展示各平台价格对比，高亮最低价
- 显示产品链接，方便查看详情

### 手动录入
- 选择监控项目录入价格
- 自动检测预警条件
- 录入后自动刷新数据

## API接口

### 获取价格数据
```
GET /api/prices
```

### 获取预警列表
```
GET /api/alerts
```

### 手动录入价格
```
POST /api/manual-entry
Content-Type: application/json

{
    "item_id": "M001",
    "price": 85000.00
}
```

### 扫描价格
```
GET /api/scrape/{keyword}
```

### 处理预警
```
POST /api/resolve-alert/{alert_id}
```

### 健康检查
```
GET /health
```

## 命令行操作

### 场景1：批量价格录入（推荐每周一次）

```bash
python monitor.py batch
```

按提示逐项输入当前市场价格，系统自动检测预警。

### 场景2：自动扫描电商平台价格

```bash
python monitor.py scrape           # 扫描所有监控项目
python monitor.py scrape M001     # 扫描指定项目
python monitor.py scrape M001 M005 # 扫描多个指定项目
python monitor.py scrape --auto    # 扫描并自动记录最低价
```

### 场景3：生成价格报告

```bash
python monitor.py report  # 生成HTML可视化报告
python monitor.py export # 生成Excel数据报告
```

### 场景4：查看预警

```bash
python monitor.py check
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `batch` | 批量价格录入 |
| `scrape` | 自动扫描电商平台价格 |
| `report` | 生成HTML可视化报告 |
| `export` | 生成Excel数据报告 |
| `check` | 查看未处理预警 |
| `init` | 初始化数据库 |
| `help` | 显示帮助信息 |

## 监控项目清单

共28项核心监控部件，涵盖8大品类：

| ID | 品类 | 设备名称 | 目标区间 |
|----|------|----------|----------|
| M001-M002 | AI加速卡 | 思元590/690 | ¥80,000-150,000 |
| M003-M004 | CPU | Intel 6448Y/海光7490 | ¥50,000-100,000 |
| M005-M006 | 内存 | DDR5 64GB/128GB | ¥3,500-33,000 |
| M007-M009 | SSD | PM9A3 1.92TB-7.68TB | ¥2,450-7,900 |
| M010-M011 | 电源 | CRPS 3000W | ¥0-4,999 |
| M012-M015 | 网络设备 | IB交换机/网卡 | ¥14,500-287,500 |
| M016-M020 | 网络配件 | 光模块/交换机 | ¥1,400-59,000 |
| M021-M028 | 基础设施 | CDU/UPS/机柜/变压器 | ¥4,050-450,000 |

## 价格来源

系统支持以下主流电商平台的价格抓取：

| 平台 | 网址 | 说明 |
|------|------|------|
| 京东商城 | https://search.jd.com | 国内主流3C电商平台 |
| 阿里巴巴 | https://s.1688.com | B2B批发采购平台 |
| 淘宝 | https://s.taobao.com | 综合电商平台 |
| 百度爱采购 | https://b2b.baidu.com | B2B采购平台 |

## 预警规则

1. **价格超上限预警**：当录入价格超过目标上限时触发
2. **价格低于下限预警**：当录入价格低于目标下限时触发（下限>0时）
3. **涨幅预警**：价格涨幅超过15%时触发
4. **跌幅预警**：价格跌幅超过10%时触发

预警触发后系统会自动发送邮件通知。

## 故障排查

| 问题 | 排查方法 | 解决方案 |
|------|----------|----------|
| 邮件发送失败 | 检查config.json SMTP配置 | 确认邮箱开启SMTP，使用授权码而非密码 |
| 定时任务不执行 | 检查crontab: `crontab -l` | 确认cron服务运行: `systemctl status cron` |
| 数据库锁定 | 检查是否有其他进程占用 | 重启程序，必要时删除 `data/*.db-journal` |
| Excel导出失败 | 检查是否安装openpyxl | `pip install openpyxl` |
| 价格抓取失败 | 检查网络连接 | 确认能访问电商平台，部分网站有反爬限制 |
| Web服务无法启动 | 检查端口是否被占用 | 更换端口或关闭占用进程 |
| API请求失败 | 检查API地址和参数 | 确认API地址正确，参数格式正确 |

## 定时任务配置

如需每周自动扫描和生成报告，可配置crontab：

```bash
crontab -e
```

添加以下内容（每周一凌晨2点执行）：

```
0 2 * * 1 cd /path/to/price-monitor && python monitor.py scrape --auto
0 3 * * 1 cd /path/to/price-monitor && python monitor.py report
0 3 * * 1 cd /path/to/price-monitor && python monitor.py export
```

## 目录结构

```
price-monitor/
├── app.py             # Flask Web应用主程序
├── monitor.py         # 命令行主程序
├── scrapers.py        # 电商价格抓取模块
├── config.json        # 配置文件
├── schema.sql         # 数据库初始化脚本
├── templates/         # Web页面模板
│   ├── base.html      # 基础模板
│   ├── index.html     # 监控概览
│   ├── alerts.html    # 预警管理
│   ├── scrape.html    # 自动扫描
│   ├── scrape_result.html # 扫描结果
│   ├── price_history.html # 价格历史
│   └── manual_entry.html  # 手动录入
├── data/              # 数据库文件目录
│   └── price_monitor.db
├── logs/              # 日志文件目录
│   └── monitor.log
└── README.md          # 说明文档
```

## 扩展开发

### 添加新的电商平台

在 `scrapers.py` 中添加新的抓取类（详见文档）。

### 添加新的监控项

1. 在 `schema.sql` 中添加新记录，包含source_url字段
2. 重新初始化数据库：`python monitor.py init`

### 添加新的Web页面

在 `templates/` 目录下创建新的HTML模板文件，然后在 `app.py` 中添加对应的路由。

## 联系方式

技术支持：请联系项目开发团队

文档更新：本文档随代码版本同步更新

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05 | 初始版本，包含28项监控、预警、报告功能 |
| v1.1 | 2026-05 | 新增自动价格扫描功能，支持京东/阿里巴巴/淘宝/百度爱采购平台抓取 |
| v1.2 | 2026-05 | 新增Web前端界面，支持可视化监控、预警管理、API接口 |