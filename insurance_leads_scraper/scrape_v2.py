#!/usr/bin/env python3
"""
28car.com 爬蟲 - 等待 JavaScript 加載完成
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

def scrape(pages=3):
    print("=" * 60)
    print("🚗 28car.com 爬蟲 (等待 JS 加載)")
    print("=" * 60)
    print("⚠️  請勿關閉瀏覽器！\n")
    
    init_db()
    total = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            for pg in range(1, pages + 1):
                print(f"\n📄 第 {pg} 頁...")
                
                url = f"https://www.28car.com/sell_lst.php" + (f"?pg={pg}" if pg > 1 else "")
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                except:
                    # 如果超時，繼續嘗試
                    pass
                
                # 等待 JavaScript 加載完成
                print("  ⏳ 等待數據加載...")
                time.sleep(12)
                
                # 找到內容 frame
                target_frame = None
                for frame in page.frames:
                    if 'sell_lst' in frame.url and '28car.com' in frame.url and frame.url != url:
                        try:
                            # 等待車輛行出現
                            frame.wait_for_selector('tr[id^="rw_"]', timeout=15000)
                            target_frame = frame
                            break
                        except:
                            pass
                
                if not target_frame:
                    print("  ⚠️ 未找到數據")
                    continue
                
                # 獲取所有車輛行
                rows = target_frame.query_selector_all('tr[id^="rw_"]')
                print(f"  找到 {len(rows)} 輛車")
                
                page_count = 0
                for row in rows:
                    try:
                        # 獲取車型
                        model_link = row.query_selector('a[href*="sell_dsp"]')
                        if not model_link:
                            continue
                        
                        car_model = model_link.inner_text().strip()
                        href = model_link.get_attribute('href') or ''
                        
                        # 提取 vid
                        vid_match = re.search(r'h_vid=(\d+)', href)
                        if not vid_match:
                            continue
                        vid = vid_match.group(1)
                        
                        # 獲取行內所有文本
                        row_text = row.inner_text()
                        
                        # 提取電話
                        phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', row_text)
                        if not phone_match:
                            continue
                        phone = phone_match.group(1).replace('-', '').replace(' ', '')
                        
                        # 提取價格
                        price_match = re.search(r'HK\$[\d,]+', row_text)
                        price = price_match.group(0) if price_match else ''
                        
                        # 保存
                        detail_url = f"https://www.28car.com/sell_dsp.php?h_vid={vid}"
                        if save(vid, phone, car_model, price, detail_url):
                            total += 1
                            page_count += 1
                            print(f"  ✅ [{total}] {car_model[:30]} - {phone}")
                        
                    except Exception as e:
                        continue
                
                print(f"  💾 本頁: {page_count} 條")
                time.sleep(3)
                
        finally:
            browser.close()
    
    print(f"\n{'=' * 60}")
    print(f"✅ 總共: {total} 條")
    
    # 導出 Excel
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT model 車型, phone 電話, price 價格, url 鏈接 FROM leads", conn)
    conn.close()
    if not df.empty:
        excel_path = DATA_DIR / f"潛客_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(excel_path, index=False)
        print(f"📊 Excel: {excel_path}")
    
    print(f"{'=' * 60}")

if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    scrape(pages=p)
