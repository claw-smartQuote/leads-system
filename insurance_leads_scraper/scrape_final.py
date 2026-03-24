#!/usr/bin/env python3
"""
28car.com 爬蟲 - 簡化版本
直接獲取 frame HTML 然後用正則解析
"""

import time
import re
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

DATA_DIR = Path.home() / "Desktop" / "汽車保險潛客數據"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "leads.db"
EXCEL_PATH = DATA_DIR / f"潛客_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY, post_id TEXT UNIQUE, phone TEXT UNIQUE,
        model TEXT, price TEXT, url TEXT, date TEXT)''')
    conn.commit()
    conn.close()

def save(post_id, phone, model, price, url):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO leads VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                  (post_id, phone, model, price, url, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return c.rowcount > 0
    except:
        return False

def export():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql("SELECT model 車型, phone 電話, price 價格, url 鏈接 FROM leads", conn)
        if not df.empty:
            df.to_excel(EXCEL_PATH, index=False)
            print(f"📊 Excel: {EXCEL_PATH} ({len(df)} 條)")
    except:
        # 列名可能是 car_model
        df = pd.read_sql("SELECT car_model 車型, phone 電話, price 價格, url 鏈接 FROM leads", conn)
        if not df.empty:
            df.to_excel(EXCEL_PATH, index=False)
            print(f"📊 Excel: {EXCEL_PATH} ({len(df)} 條)")
    conn.close()
    return df

def parse_cars(html):
    """從 HTML 中提取車輛"""
    cars = []
    
    # 找到所有 sell_dsp 鏈接
    pattern = r'<a[^>]*href="([^"]*sell_dsp\.php[^"]*)"[^>]*>([^<]{3,40})</a>'
    matches = re.findall(pattern, html, re.IGNORECASE)
    
    for href, model in matches:
        # 提取 vid
        vid_match = re.search(r'h_vid=(\d+)', href)
        if not vid_match:
            continue
        vid = vid_match.group(1)
        
        model = model.strip()
        if not model or '$' in model or len(model) < 3:
            continue
        
        # 在這個鏈接周圍的內容中找電話
        # 找到這個鏈接在 HTML 中的位置
        pos = html.find(href)
        if pos == -1:
            continue
        
        # 提取周圍 1000 字符
        surrounding = html[max(0, pos-500):min(len(html), pos+500)]
        
        # 找電話
        phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', surrounding)
        if not phone_match:
            continue
        phone = phone_match.group(1).replace('-', '').replace(' ', '')
        
        # 找價格
        price_match = re.search(r'HK\$[\d,]+', surrounding)
        price = price_match.group(0) if price_match else ''
        
        url = f"https://www.28car.com/sell_dsp.php?h_vid={vid}"
        
        cars.append({'vid': vid, 'model': model, 'phone': phone, 'price': price, 'url': url})
    
    return cars

def scrape(pages=3):
    print("=" * 60)
    print("🚗 28car.com 爬蟲")
    print("=" * 60)
    print("⚠️  請勿關閉瀏覽器！\n")
    
    init_db()
    total = 0
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            for pg in range(1, pages + 1):
                print(f"\n📄 第 {pg} 頁...")
                
                url = f"https://www.28car.com/sell_lst.php" + (f"?pg={pg}" if pg > 1 else "")
                page.goto(url, wait_until='networkidle', timeout=60000)
                time.sleep(8)
                
                # 獲取包含數據的 frame
                target_frame = None
                for frame in page.frames:
                    if 'sell_lst' in frame.url and '28car.com' in frame.url and frame.url != url:
                        try:
                            html = frame.content()
                            if len(html) > 100000:
                                target_frame = frame
                                break
                        except:
                            pass
                
                if not target_frame:
                    print("  ⚠️ 未找到內容")
                    continue
                
                html = target_frame.content()
                print(f"  HTML 長度: {len(html)}")
                
                # 保存 HTML 調試
                debug_path = DATA_DIR / f"debug_page_{pg}.html"
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html[:50000])  # 只保存前 50KB
                print(f"  💾 HTML 已保存: {debug_path}")
                
                # 解析
                cars = parse_cars(html)
                print(f"  找到 {len(cars)} 輛車")
                
                new_count = 0
                for car in cars:
                    key = car['vid'] + car['phone']
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    if save(car['vid'], car['phone'], car['model'], car['price'], car['url']):
                        total += 1
                        new_count += 1
                        print(f"  ✅ [{total}] {car['model'][:30]} - {car['phone']}")
                
                print(f"  💾 新保存: {new_count} 條")
                time.sleep(3)
                
        finally:
            browser.close()
    
    print(f"\n{'=' * 60}")
    print(f"✅ 總共: {total} 條")
    export()
    print(f"{'=' * 60}")

if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    scrape(pages=p)
