#!/usr/bin/env python3
"""
直接從 28car.com 詳情頁獲取電話
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

def scrape_detail(post_id):
    """訪問詳情頁獲取電話"""
    return {'phone': '', 'model': '', 'price': ''}

def scrape_list_page(page, max_cars=20):
    """從列表頁獲取車輛鏈接然後訪問詳情"""
    results = []
    
    time.sleep(8)  # 等待加載
    
    # 找 frame
    target_frame = None
    for frame in page.frames:
        if 'sell_lst' in frame.url and '28car.com' in frame.url:
            if frame.url != page.url:
                try:
                    if len(frame.content()) > 100000:
                        target_frame = frame
                        break
                except:
                    pass
    
    if not target_frame:
        print("    未找到內容frame")
        return results
    
    # 找所有車輛鏈接
    links = target_frame.query_selector_all('a[href*="sell_dsp"]')
    print(f"    找到 {len(links)} 個鏈接")
    
    count = 0
    for link in links:
        try:
            href = link.get_attribute('href') or ''
            vid_match = re.search(r'h_vid=(\d+)', href)
            if not vid_match:
                continue
            
            vid = vid_match.group(1)
            model = link.inner_text().strip()
            
            if not model or len(model) < 3 or '$' in model:
                continue
            
            # 訪問詳情頁
            detail_url = f"https://www.28car.com/sell_dsp.php?h_vid={vid}"
            page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            # 獲取頁面內容
            page_text = page.inner_text('body')
            
            # 找電話
            phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', page_text)
            if phone_match:
                phone = phone_match.group(1).replace('-', '').replace(' ', '')
                
                # 找價格
                price_match = re.search(r'HK\$[\d,]+', page_text)
                price = price_match.group(0) if price_match else ''
                
                results.append({
                    'vid': vid,
                    'model': model,
                    'phone': phone,
                    'price': price,
                    'url': detail_url
                })
                count += 1
                print(f"    ✅ [{count}] {model[:30]} - {phone}")
            
            # 返回列表頁
            page.go_back()
            time.sleep(2)
            
            if count >= max_cars:
                break
                
        except Exception as e:
            print(f"    錯誤: {e}")
            try:
                page.go_back()
                time.sleep(2)
            except:
                pass
    
    return results

def run(pages=2):
    print("=" * 60)
    print("🚗 28car.com 電話獲取")
    print("=" * 60)
    print("⚠️ 請勿關閉瀏覽器！\n")
    
    init_db()
    total = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            for pg in range(1, pages + 1):
                print(f"\n📄 第 {pg} 頁...")
                
                url = "https://www.28car.com/sell_lst.php"
                if pg > 1:
                    url += f"?pg={pg}"
                
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                
                cars = scrape_list_page(page, max_cars=15)
                
                for car in cars:
                    if save(car['vid'], car['phone'], car['model'], car['price'], car['url']):
                        total += 1
                
                print(f"    本頁: {len(cars)} 輛")
                
        finally:
            browser.close()
    
    # 導出
    print(f"\n{'=' * 60}")
    print(f"✅ 總共: {total} 條")
    
    if total > 0:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql("SELECT model, phone, price, url FROM leads", conn)
            conn.close()
            excel = DATA_DIR / f"潛客_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            df.to_excel(excel, index=False)
            print(f"📊 Excel: {excel}")
        except Exception as e:
            print(f"導出錯誤: {e}")
    
    print(f"{'=' * 60}")

if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    run(pages=p)
