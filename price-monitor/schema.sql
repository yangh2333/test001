CREATE TABLE IF NOT EXISTS monitor_items (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    device_name TEXT NOT NULL,
    target_upper_limit REAL NOT NULL,
    target_lower_limit REAL NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    price REAL NOT NULL,
    record_date TEXT NOT NULL,
    source TEXT DEFAULT 'manual',
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES monitor_items(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_resolved INTEGER DEFAULT 0,
    FOREIGN KEY (item_id) REFERENCES monitor_items(id)
);

CREATE TABLE IF NOT EXISTS price_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    is_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO monitor_items (id, category, device_name, target_upper_limit, target_lower_limit, source_url) VALUES
('M001', 'AI加速卡', '思元590', 150000.00, 80000.00, 'https://search.jd.com/Search?keyword=思元590&enc=utf-8'),
('M002', 'AI加速卡', '思元690', 150000.00, 80000.00, 'https://search.jd.com/Search?keyword=思元690&enc=utf-8'),
('M003', 'CPU', 'Intel 6448Y', 100000.00, 50000.00, 'https://search.jd.com/Search?keyword=Intel+6448Y&enc=utf-8'),
('M004', 'CPU', '海光7490', 100000.00, 50000.00, 'https://search.jd.com/Search?keyword=海光7490&enc=utf-8'),
('M005', '内存', 'DDR5 64GB', 33000.00, 3500.00, 'https://search.jd.com/Search?keyword=DDR5+64GB&enc=utf-8'),
('M006', '内存', 'DDR5 128GB', 33000.00, 3500.00, 'https://search.jd.com/Search?keyword=DDR5+128GB&enc=utf-8'),
('M007', 'SSD', 'PM9A3 1.92TB', 7900.00, 2450.00, 'https://search.jd.com/Search?keyword=PM9A3+1.92TB&enc=utf-8'),
('M008', 'SSD', 'PM9A3 3.84TB', 7900.00, 2450.00, 'https://search.jd.com/Search?keyword=PM9A3+3.84TB&enc=utf-8'),
('M009', 'SSD', 'PM9A3 7.68TB', 7900.00, 2450.00, 'https://search.jd.com/Search?keyword=PM9A3+7.68TB&enc=utf-8'),
('M010', '电源', 'CRPS 3000W', 4999.00, 0.00, 'https://search.jd.com/Search?keyword=CRPS+3000W&enc=utf-8'),
('M011', '电源', 'CRPS 3000W 冗余', 4999.00, 0.00, 'https://search.jd.com/Search?keyword=CRPS+3000W+冗余电源&enc=utf-8'),
('M012', '网络设备', 'IB交换机 36口', 287500.00, 14500.00, 'https://search.jd.com/Search?keyword=IB交换机+36口&enc=utf-8'),
('M013', '网络设备', 'IB交换机 72口', 287500.00, 14500.00, 'https://search.jd.com/Search?keyword=IB交换机+72口&enc=utf-8'),
('M014', '网络设备', 'IB网卡 单口', 287500.00, 14500.00, 'https://search.jd.com/Search?keyword=IB网卡+单口&enc=utf-8'),
('M015', '网络设备', 'IB网卡 双口', 287500.00, 14500.00, 'https://search.jd.com/Search?keyword=IB网卡+双口&enc=utf-8'),
('M016', '网络配件', '光模块 100G', 59000.00, 1400.00, 'https://search.jd.com/Search?keyword=光模块+100G&enc=utf-8'),
('M017', '网络配件', '光模块 200G', 59000.00, 1400.00, 'https://search.jd.com/Search?keyword=光模块+200G&enc=utf-8'),
('M018', '网络配件', '以太网交换机 24口', 59000.00, 1400.00, 'https://search.jd.com/Search?keyword=以太网交换机+24口&enc=utf-8'),
('M019', '网络配件', '以太网交换机 48口', 59000.00, 1400.00, 'https://search.jd.com/Search?keyword=以太网交换机+48口&enc=utf-8'),
('M020', '网络配件', 'DAC线缆', 59000.00, 1400.00, 'https://search.jd.com/Search?keyword=DAC线缆&enc=utf-8'),
('M021', '基础设施', 'CDU 风冷', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=CDU+风冷&enc=utf-8'),
('M022', '基础设施', 'CDU 液冷', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=CDU+液冷&enc=utf-8'),
('M023', '基础设施', 'UPS 10KVA', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=UPS+10KVA&enc=utf-8'),
('M024', '基础设施', 'UPS 20KVA', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=UPS+20KVA&enc=utf-8'),
('M025', '基础设施', '服务器机柜 42U', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=服务器机柜+42U&enc=utf-8'),
('M026', '基础设施', '服务器机柜 48U', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=服务器机柜+48U&enc=utf-8'),
('M027', '基础设施', '变压器 10KVA', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=变压器+10KVA&enc=utf-8'),
('M028', '基础设施', '变压器 20KVA', 450000.00, 4050.00, 'https://search.jd.com/Search?keyword=变压器+20KVA&enc=utf-8');

INSERT OR IGNORE INTO price_sources (source_name, source_type, base_url, is_enabled) VALUES
('京东商城', 'jd', 'https://search.jd.com/Search', 1),
('阿里巴巴', 'alibaba', 'https://s.1688.com/jofferSearch', 1),
('淘宝', 'taobao', 'https://s.taobao.com/search', 1);