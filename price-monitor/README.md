# 价格监控系统 v1.1

## 项目简介

价格监控系统用于监控数据中心核心部件的市场价格变化，支持28项监控项目，涵盖8大品类。系统支持价格录入、自动价格扫描、预警检测、报告生成等功能。

## 技术栈

- Python 3.6+
- SQLite 数据库
- requests（网页抓取）
- beautifulsoup4（HTML解析）
- openpyxl（Excel导出）

## 快速开始

### 1. 安装依赖

```bash
pip install requests beautifulsoup4 openpyxl
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

### 场景2：自动扫描电商平台价格（新增）

自动扫描京东、阿里巴巴、淘宝等主流电商平台的实时价格：

```bash
python monitor.py scrape           # 扫描所有监控项目
python monitor.py scrape M001     # 扫描指定项目
python monitor.py scrape M001 M005 # 扫描多个指定项目
python monitor.py scrape --auto    # 扫描并自动记录最低价到数据库
```

扫描完成后，系统会显示各平台的最低价格及产品链接。

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

| ID | 品类 | 设备名称 | 目标区间 | 查询链接 |
|----|------|----------|----------|----------|
| M001-M002 | AI加速卡 | 思元590/690 | ¥80,000-150,000 | 京东搜索 |
| M003-M004 | CPU | Intel 6448Y/海光7490 | ¥50,000-100,000 | 京东搜索 |
| M005-M006 | 内存 | DDR5 64GB/128GB | ¥3,500-33,000 | 京东搜索 |
| M007-M009 | SSD | PM9A3 1.92TB-7.68TB | ¥2,450-7,900 | 京东搜索 |
| M010-M011 | 电源 | CRPS 3000W | ¥0-4,999 | 京东搜索 |
| M012-M015 | 网络设备 | IB交换机/网卡 | ¥14,500-287,500 | 京东搜索 |
| M016-M020 | 网络配件 | 光模块/交换机 | ¥1,400-59,000 | 京东搜索 |
| M021-M028 | 基础设施 | CDU/UPS/机柜/变压器 | ¥4,050-450,000 | 京东搜索 |

## 价格来源

系统支持以下主流电商平台的价格抓取：

| 平台 | 网址 | 说明 |
|------|------|------|
| 京东商城 | https://search.jd.com | 国内主流3C电商平台 |
| 阿里巴巴 | https://s.1688.com | B2B批发采购平台 |
| 淘宝 | https://s.taobao.com | 综合电商平台 |
| 百度爱采购 | https://b2b.baidu.com | B2B采购平台 |

每个监控项目都关联了京东搜索链接，可在报告中直接点击查看。

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
| 抓取被拦截 | 请求频率过高 | 系统已内置延迟机制，避免请求过快 |

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
├── monitor.py        # 主程序
├── scrapers.py       # 电商价格抓取模块
├── config.json       # 配置文件
├── schema.sql        # 数据库初始化脚本
├── data/             # 数据库文件目录
│   └── price_monitor.db
├── logs/             # 日志文件目录
│   └── monitor.log
└── README.md         # 说明文档
```

## 数据库表结构

### monitor_items - 监控项目表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 项目ID（如M001） |
| category | TEXT | 品类 |
| device_name | TEXT | 设备名称 |
| target_upper_limit | REAL | 目标价格上限 |
| target_lower_limit | REAL | 目标价格下限 |
| source_url | TEXT | 电商平台搜索链接 |

### price_records - 价格记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| item_id | TEXT | 监控项目ID |
| price | REAL | 价格 |
| record_date | TEXT | 记录日期 |
| source | TEXT | 来源（manual/scrape_jd等） |
| source_url | TEXT | 产品链接 |

### alerts - 预警记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| item_id | TEXT | 监控项目ID |
| alert_type | TEXT | 预警类型 |
| message | TEXT | 预警信息 |
| triggered_at | TIMESTAMP | 触发时间 |
| is_resolved | INTEGER | 是否已处理 |

## 扩展开发

### 添加新的电商平台

在 `scrapers.py` 中添加新的抓取类：

```python
class NewPlatformScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = 'newplatform'
        self.display_name = '新平台'
        self.base_url = 'https://search.example.com'
    
    def build_url(self, keyword):
        params = {'q': keyword}
        return f"{self.base_url}?{urlencode(params)}"
    
    def scrape(self, keyword):
        url = self.build_url(keyword)
        html = self.fetch_page(url, delay=2)
        if not html:
            return {'success': False, 'prices': [], 'source': self.display_name}
        
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        for item in soup.select('.product-item'):
            try:
                price = float(item.select_one('.price').text)
                title = item.select_one('.title').text
                product_url = item.select_one('a').get('href')
                prices.append({
                    'price': price,
                    'title': title.strip(),
                    'url': product_url
                })
            except (ValueError, AttributeError):
                continue
        
        return {
            'success': len(prices) > 0,
            'prices': sorted(prices, key=lambda x: x['price'])[:5],
            'source': self.display_name,
            'url': url
        }
```

然后在 `get_scraper()` 函数中注册新平台。

### 添加新的监控项

1. 在 `schema.sql` 中添加新记录，包含source_url字段
2. 重新初始化数据库：`python monitor.py init`

## 联系方式

技术支持：请联系项目开发团队

文档更新：本文档随代码版本同步更新

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05 | 初始版本，包含28项监控、预警、报告功能 |
| v1.1 | 2026-05 | 新增自动价格扫描功能，支持京东/阿里巴巴/淘宝/百度爱采购平台抓取，价格项保留网络地址 |