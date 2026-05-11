#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor import (
    init_database,
    get_monitor_items,
    get_latest_price,
    get_unresolved_alerts,
    resolve_alert,
    insert_price_record,
    insert_alert,
    check_alerts,
    get_db_connection
)
from scrapers import scrape_all_sources

app = Flask(__name__)
CORS(app)

@app.template_filter('format_number')
def format_number(value):
    return '{:,.2f}'.format(value)

@app.route('/')
def index():
    init_database()
    items = get_monitor_items()
    price_stats = []
    alert_count = 0
    
    for item in items:
        item_id, category, device_name, target_upper, target_lower, source_url = item
        latest = get_latest_price(item_id)
        
        status = "normal"
        status_text = "正常"
        price = None
        record_date = None
        
        if latest:
            price, record_date = latest
            if price > target_upper:
                status = "warning"
                status_text = "超上限"
                alert_count += 1
            elif target_lower > 0 and price < target_lower:
                status = "warning"
                status_text = "低于下限"
                alert_count += 1
        
        price_stats.append({
            'id': item_id,
            'category': category,
            'device_name': device_name,
            'price': price,
            'record_date': record_date,
            'target_upper': target_upper,
            'target_lower': target_lower,
            'status': status,
            'status_text': status_text,
            'source_url': source_url
        })
    
    unresolved_alerts = get_unresolved_alerts()
    alert_count = len(unresolved_alerts)
    
    return render_template('index.html', 
                           price_stats=price_stats, 
                           alert_count=alert_count,
                           current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/price-history/<item_id>')
def price_history(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM monitor_items WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    
    cursor.execute('SELECT price, record_date, source, source_url FROM price_records WHERE item_id = ? ORDER BY record_date DESC', (item_id,))
    records = cursor.fetchall()
    
    conn.close()
    
    history_data = []
    for record in records:
        history_data.append({
            'price': record[0],
            'record_date': record[1],
            'source': record[2],
            'source_url': record[3]
        })
    
    return render_template('price_history.html',
                           item_id=item_id,
                           item=item,
                           history_data=history_data)

@app.route('/alerts')
def alerts():
    unresolved_alerts = get_unresolved_alerts()
    
    alert_list = []
    for alert in unresolved_alerts:
        alert_id, item_id, alert_type, message, triggered_at, device_name = alert
        alert_list.append({
            'id': alert_id,
            'item_id': item_id,
            'alert_type': alert_type,
            'message': message,
            'triggered_at': triggered_at,
            'device_name': device_name
        })
    
    return render_template('alerts.html', alerts=alert_list)

@app.route('/resolve-alert/<alert_id>', methods=['POST'])
def resolve_alert_endpoint(alert_id):
    try:
        resolve_alert(alert_id)
        return jsonify({'success': True, 'message': '预警已标记为已处理'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/scrape', methods=['GET', 'POST'])
def scrape_page():
    if request.method == 'POST':
        item_id = request.form.get('item_id', 'all')
        
        if item_id == 'all':
            items = get_monitor_items()
        else:
            items = [item for item in get_monitor_items() if item[0] == item_id]
        
        results = []
        for item in items:
            item_id, category, device_name, target_upper, target_lower, source_url = item
            scrape_result = scrape_all_sources(device_name)
            
            valid_prices = []
            for source_result in scrape_result:
                if source_result.get('success') and source_result.get('prices'):
                    for price_info in source_result['prices']:
                        valid_prices.append({
                            'source': source_result['source'],
                            'price': price_info['price'],
                            'title': price_info['title'],
                            'url': price_info['url']
                        })
            
            if valid_prices:
                min_price = min(valid_prices, key=lambda x: x['price'])
                results.append({
                    'item_id': item_id,
                    'device_name': device_name,
                    'category': category,
                    'prices': valid_prices[:5],
                    'lowest_price': min_price['price'],
                    'lowest_source': min_price['source'],
                    'lowest_url': min_price['url']
                })
            else:
                results.append({
                    'item_id': item_id,
                    'device_name': device_name,
                    'category': category,
                    'prices': [],
                    'lowest_price': None,
                    'lowest_source': None,
                    'lowest_url': None
                })
        
        return render_template('scrape_result.html', results=results)
    
    items = get_monitor_items()
    return render_template('scrape.html', items=items)

@app.route('/manual-entry', methods=['GET', 'POST'])
def manual_entry():
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        price = float(request.form.get('price'))
        
        insert_price_record(item_id, price)
        items = get_monitor_items()
        item = next((i for i in items if i[0] == item_id), None)
        if item:
            check_alerts(item_id, price, item)
        
        return redirect(url_for('index'))
    
    items = get_monitor_items()
    return render_template('manual_entry.html', items=items)

@app.route('/api/prices')
def api_prices():
    items = get_monitor_items()
    data = []
    
    for item in items:
        item_id, category, device_name, target_upper, target_lower, source_url = item
        latest = get_latest_price(item_id)
        
        status = "normal"
        if latest:
            price, record_date = latest
            if price > target_upper:
                status = "warning"
            elif target_lower > 0 and price < target_lower:
                status = "warning"
            
            data.append({
                'item_id': item_id,
                'category': category,
                'device_name': device_name,
                'price': price,
                'record_date': record_date,
                'target_upper': target_upper,
                'target_lower': target_lower,
                'status': status,
                'source_url': source_url
            })
    
    return jsonify(data)

@app.route('/api/alerts')
def api_alerts():
    unresolved_alerts = get_unresolved_alerts()
    data = []
    
    for alert in unresolved_alerts:
        alert_id, item_id, alert_type, message, triggered_at, device_name = alert
        data.append({
            'id': alert_id,
            'item_id': item_id,
            'alert_type': alert_type,
            'message': message,
            'triggered_at': triggered_at,
            'device_name': device_name
        })
    
    return jsonify(data)

@app.route('/api/scrape/<keyword>')
def api_scrape(keyword):
    results = scrape_all_sources(keyword)
    return jsonify(results)

@app.route('/api/manual-entry', methods=['POST'])
def api_manual_entry():
    data = request.json
    item_id = data.get('item_id')
    price = data.get('price')
    
    if not item_id or price is None:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    try:
        insert_price_record(item_id, float(price))
        items = get_monitor_items()
        item = next((i for i in items if i[0] == item_id), None)
        if item:
            check_alerts(item_id, float(price), item)
        return jsonify({'success': True, 'message': '价格记录成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/resolve-alert/<alert_id>', methods=['POST'])
def api_resolve_alert(alert_id):
    try:
        resolve_alert(alert_id)
        return jsonify({'success': True, 'message': '预警已处理'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)