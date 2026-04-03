#!/usr/bin/env python3
"""
28car.com 簡化版爬蟲 - 專門繞過 Cloudflare
"""

import time
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# 設置路徑
DATA_DIR = Path.home() / "Desktop" / "汽車保險潛客數據"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "leads_database.db"

def init_db():
    """初始化數據庫"""
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
            first_seen_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def is_duplicate(post_id, phone):
    """檢查是否重複"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM car_leads WHERE post_id = ? OR phone = ?", (post_id, phone))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_lead(car_model, price, phone, post_url, post_id):
    """保存線索"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO car_leads (post_id, phone, car_model, price, post_url, seller_type, first_seen_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (post_id, phone, car_model, price, post_url, '私人', datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        print(f"    ✅ 已保存: {car_model} - {phone}")
        return True
    except sqlite3.IntegrityError:
        print(f"    ⏭️  重複: {car_model}")
        return False
    finally:
        conn.close()

def scrape_28car(max_pages=5):
    """爬取 28car.com"""
    print("="*60)
    print("🚗 28car.com 爬蟲")
    print("="*60)
    print(f"📂 數據保存到: {DATA_DIR}")
    print(f"📄 目標: {max_pages} 頁")
    print("="*60)
    
    init_db()
    
    leads_count = 0
    
    with sync_playwright() as p:
        # 使用有頭模式繞過 Cloudflare
        print("\n🌐 啟動瀏覽器...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            for page_num in range(1, max_pages + 1):
                print(f"\n📄 處理第 {page_num} 頁...")
                
                # 構建 URL
                url = f"https://www.28car.com/sell_lst.php"
                if page_num > 1:
                    url += f"?pg={page_num}"
                
                # 訪問頁面
                page.goto(url, wait_until='networkidle', timeout=60000)
                print(f"   頁面已載入")
                
                # 等待 iframe 載入
                print(f"   等待內容載入...")
                time.sleep(8)
                
                # 找到正確的 frame
                target_frame = None
                for frame in page.frames:
                    frame_url = frame.url
                    if 'sell_lst' in frame_url and '28car.com' in frame_url and len(frame_url) > 50:
                        target_frame = frame
                        print(f"   ✅ 找到內容 frame")
                        break
                
                if not target_frame:
                    print(f"   ⚠️ 未找到內容 frame，跳過")
                    continue
                
                # 獲取表格行
                rows = target_frame.query_selector_all('tr')
                print(f"   找到 {len(rows)} 行")
                
                page_leads = 0
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) < 5:
                            continue
                        
                        # 獲取車型
                        model_cell = cells[1]
                        model_link = model_cell.query_selector('a')
                        if not model_link:
                            continue
                            
                        car_model = model_link.inner_text().strip()
                        detail_url = model_link.get_attribute('href') or ''
                        
                        if not car_model or len(car_model) < 3 or '$' in car_model:
                            continue
                        
                        # 獲取描述（可能包含電話）
                        desc_cell = cells[2] if len(cells) > 2 else None
                        desc_text = desc_cell.inner_text().strip() if desc_cell else ''
                        
                        # 獲取價格
                        price_text = ''
                        for idx in [3, 4]:
                            if idx < len(cells):
                                text = cells[idx].inner_text().strip()
                                if '$' in text or 'HK' in text:
                                    price_text = text
                                    break
                        
                        # 提取電話
                        phone_match = re.search(r'(?:電話|Tel)[:\s]*(\d{4}[\s-]?\d{4})', desc_text)
                        if not phone_match:
                            continue
                            
                        phone = phone_match.group(1).replace('-', '').replace(' ', '')
                        
                        # 提取 ID
                        post_id = ''
                        if detail_url:
                            vid_match = re.search(r'h_vid=(\d+)', detail_url)
                            post_id = vid_match.group(1) if vid_match else ''
                        
                        # 構建完整 URL
                        if detail_url and not detail_url.startswith('http'):
                            detail_url = 'https://www.28car.com/' + detail_url.lstrip('/')
                        
                        # 檢查重複並保存
                        if is_duplicate(post_id, phone):
                            continue
                        
                        if save_lead(car_model, price_text, phone, detail_url, post_id):
                            leads_count += 1
                            page_leads += 1
                            
                    except Exception as e:
                        continue
                
                print(f"   📊 第 {page_num} 頁完成，獲取 {page_leads} 條")
                
                # 延遲避免被封
                time.sleep(3)
                
        finally:
            browser.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 爬蟲完成！")
    print(f"📊 總共獲取 {leads_count} 條新線索")
    print(f"🗄️  數據庫: {DB_PATH}")
    print(f"{'='*60}")

if __name__ == "__main__":
    import sys
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    scrape_28car(max_pages=pages)
