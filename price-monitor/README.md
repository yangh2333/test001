# 价格监控系统 v1.0

## 项目简介

价格监控系统用于监控数据中心核心部件的市场价格变化，支持28项监控项目，涵盖8大品类。系统支持价格录入、预警检测、报告生成等功能。

## 技术栈

- Python 3.6+
- SQLite 数据库
- openpyxl（Excel导出）

## 快速开始

### 1. 安装依赖

```bash
pip install openpyxl
```

### 2. 配置修改

编辑 `config.json` 配置文件：

```json
{
    "smtp": {
        "server": "smtp.example.com",
        "port": 587,
        "username": "your_email@example.com",
        "password": "your_auth_code",
        "from_address": "your_email@example.com",
        "to_addresses": ["admin@example.com"],
        "use_tls": true
    },
    "alert": {
        "price_increase_threshold": 0.15,
        "price_decrease_threshold": 0.10
    },
    "database": {
        "path": "data/price_monitor.db"
    },
    "logging": {
        "level": "INFO",
        "file": "logs/monitor.log"
    }
}
```

### 3. 初始化数据库

```bash
python monitor.py init
```

## 日常操作

### 场景1：批量价格录入（推荐每周一次）

```bash
python monitor.py batch
```

按提示逐项输入当前市场价格，系统自动检测预警。

### 场景2：生成价格报告

```bash
python monitor.py report  # 生成HTML可视化报告
python monitor.py export  # 生成Excel数据报告
```

### 场景3：查看预警

```bash
python monitor.py check
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `batch` | 批量价格录入 |
| `report` | 生成HTML可视化报告 |
| `export` | 生成Excel数据报告 |
| `check` | 查看未处理预警 |
| `init` | 初始化数据库 |
| `help` | 显示帮助信息 |

## 监控项目清单

共28项核心监控部件，涵盖8大品类：

| 品类 | 设备名称 | 目标上限 |
|------|----------|----------|
| AI加速卡 | 思元590/690 | ¥80,000-150,000 |
| CPU | Intel 6448Y / 海光7490 | ¥50,000-100,000 |
| 内存 | DDR5 64GB/128GB | ¥3,500-33,000 |
| SSD | PM9A3 1.92TB-7.68TB | ¥2,450-7,900 |
| 电源 | CRPS 3000W | ¥4,999 |
| 网络设备 | IB交换机/网卡 | ¥14,500-287,500 |
| 网络配件 | 光模块/以太网交换机 | ¥1,400-59,000 |
| 基础设施 | CDU/UPS/机柜/变压器 | ¥4,050-450,000 |

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

## 定时任务配置

如需每周自动生成报告，可配置crontab：

```bash
crontab -e
```

添加以下内容（每周一凌晨2点执行）：

```
0 2 * * 1 cd /path/to/price-monitor && python monitor.py report
0 2 * * 1 cd /path/to/price-monitor && python monitor.py export
```

## 目录结构

```
price-monitor/
├── monitor.py        # 主程序
├── config.json       # 配置文件
├── schema.sql        # 数据库初始化脚本
├── data/             # 数据库文件目录
│   └── price_monitor.db
├── logs/             # 日志文件目录
│   └── monitor.log
└── README.md         # 说明文档
```

## 扩展开发

### 添加电商自动抓取

在 `monitor.py` 中添加抓取函数：

```python
def scrape_jd(keyword):
    """京东搜索抓取（需Selenium/Playwright）"""
    # 使用Selenium自动化浏览器
    # 或使用京东联盟API
    pass
```

### 添加新的监控项

1. 在 `schema.sql` 中添加新记录
2. 重新初始化数据库：`python monitor.py init`

## 联系方式

技术支持：请联系项目开发团队

文档更新：本文档随代码版本同步更新

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05 | 初始版本，包含28项监控、预警、报告功能 |