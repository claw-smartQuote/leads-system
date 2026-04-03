#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
28car.com 爬蟲 - 可靠版本
使用 HTML 解析方式提取數據
"""

import os
import re
import time
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# 設置路徑
DESKTOP_DIR = Path.home() / "Desktop"
DATA_FOLDER = DESKTOP_DIR / "汽車保險潛客數據"
DATA_FOLDER.mkdir(exist_ok=True)

DB_PATH = DATA_FOLDER / "leads_database.db"
EXCEL_PATH = DATA_FOLDER / f"保險潛客數據_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

print(f"📂 數據保存位置: {DATA_FOLDER}")

# ============ 數據庫 ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS car_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            phone TEXT UNIQUE,
            car_model TEXT,
            price TEXT,
            seller_name TEXT,
            post_url TEXT,
            seller_type TEXT,
            scrape_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def is_duplicate(post_id, phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM car_leads WHERE post_id = ? OR phone = ?", (post_id, phone))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_lead(car_model, price, phone, post_url, post_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO car_leads (post_id, phone, car_model, price, post_url, seller_type, scrape_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (post_id, phone, car_model, price, post_url, '私人', datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ============ Excel 導出 ============
def export_to_excel():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM car_leads ORDER BY id DESC", conn)
    conn.close()
    
    if df.empty:
        print("⚠️ 沒有數據")
        return None
    
    # 重命名列
    df = df.rename(columns={
        'car_model': '車輛型號',
        'price': '售價',
        'phone': '電話號碼',
        'seller_type': '賣家類型',
        'post_url': '帖子鏈接',
        'post_id': '帖子ID',
        'scrape_date': '抓取日期'
    })
    
    columns = ['車輛型號', '售價', '電話號碼', '賣家類型', '帖子鏈接', '帖子ID', '抓取日期']
    df = df[[col for col in columns if col in df.columns]]
    
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='28Car_潛客')
    
    print(f"✅ Excel 保存: {EXCEL_PATH}")
    return EXCEL_PATH

# ============ 爬蟲 ============
def scrape_page(html):
    """從 HTML 中提取車輛數據"""
    cars = []
    
    # 找到所有車輛塊 - 通過 sell_dsp.php 鏈接
    # 模式: sell_dsp.php?h_vid=123456
    car_pattern = r'sell_dsp\.php\?h_vid=(\d+)[^>]*>([^<]{3,50})</a>'
    matches = re.findall(car_pattern, html)
    
    for match in matches:
        post_id, car_model = match
        car_model = car_model.strip()
        
        if not car_model or len(car_model) < 2:
            continue
        
        # 找價格 - 在車型附近的 $ 或 HK
        # 查找這個車型周圍的內容
        price_pattern = rf'sell_dsp\.php\?h_vid={post_id}[^>]*>[^<]*</a>.*?(\$[\d,]+)'
        price_match = re.search(price_pattern, html, re.DOTALL)
        price = price_match.group(1) if price_match else ''
        
        # 找電話 - 整個頁面中搜索 8位數字
        phone_pattern = r'(?:電話|Tel|聯絡)[:\s]*(\d{4}[\s\-]?\d{4})'
        
        # 獲取完整的車輛區塊
        block_pattern = rf'sell_dsp\.php\?h_vid={post_id}[^>]*>([^<]*)</a>.*?(?:</tr>|<tr)'
        block_match = re.search(block_pattern, html, re.DOTALL)
        
        phone = ''
        if block_match:
            block_text = block_match.group(0)
            phone_match = re.search(r'\b(\d{4}[\s\-]?\d{4})\b', block_text)
            if phone_match:
                phone = phone_match.group(1).replace('-', '').replace(' ', '')
        
        if not phone:
            # 從整個 HTML 中找
            all_phones = re.findall(r'\b(\d{4}[\s\-]?\d{4})\b', html)
            phone = all_phones[0].replace('-', '').replace(' ', '') if all_phones else ''
        
        if phone and car_model:
            url = f"https://www.28car.com/sell_dsp.php?h_vid={post_id}"
            cars.append({
                'model': car_model,
                'price': price,
                'phone': phone,
                'url': url,
                'post_id': post_id
            })
    
    return cars

def scrape_28car(max_pages=3, target=10):
    print("\n" + "="*50)
    print("🚗 28car.com 爬蟲 (有頭模式)")
    print("="*50)
    print(f"目標: {target} 條線索")
    print(f"⚠️ 請勿關閉瀏覽器窗口!")
    print("="*50 + "\n")
    
    init_db()
    leads_count = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            for page_num in range(1, max_pages + 1):
                if leads_count >= target:
                    break
                    
                print(f"📄 第 {page_num} 頁...")
                
                url = "https://www.28car.com/sell_lst.php"
                if page_num > 1:
                    url += f"?pg={page_num}"
                
                page.goto(url, wait_until='networkidle', timeout=60000)
                time.sleep(6)
                
                # 找 frame
                frame = None
                for f in page.frames:
                    if 'sell_lst' in f.url and '28car.com' in f.url and f.url != url:
                        if len(f.content()) > 100000:
                            frame = f
                            break
                
                if not frame:
                    print("  ⚠️ 未找到內容")
                    continue
                
                html = frame.content()
                
                # 提取數據
                cars = scrape_page(html)
                print(f"  找到 {len(cars)} 輛車")
                
                for car in cars:
                    if leads_count >= target:
                        break
                    
                    post_id = car['post_id']
                    phone = car['phone']
                    
                    if is_duplicate(post_id, phone):
                        continue
                    
                    if save_lead(car['model'], car['price'], phone, car['url'], post_id):
                        leads_count += 1
                        print(f"  ✅ [{leads_count}] {car['model'][:25]} - {phone}")
                
                time.sleep(2)
                
        finally:
            browser.close()
    
    # 導出
    print(f"\n{'='*50}")
    print(f"✅ 完成! 共獲取 {leads_count} 條")
    
    if leads_count > 0:
        export_to_excel()
    
    print(f"📁 文件位置: {DATA_FOLDER}")
    print(f"{'='*50}")

if __name__ == "__main__":
    import sys
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    scrape_28car(max_pages=pages, target=target)
