#!/usr/bin/env python3
"""
28car 車型抓取測試腳本
使用 Playwright 分析網頁結構並正確抓取車型
"""

from playwright.sync_api import sync_playwright
import re
import sqlite3
from pathlib import Path

# 初始化資料庫
db_path = Path.home() / 'Desktop/汽車保險潛客數據/test_28car.db'
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS car_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id TEXT UNIQUE,
        model TEXT,
        year TEXT,
        price TEXT,
        phone TEXT,
        details TEXT,
        created_at TEXT
    )
''')
conn.commit()

def scrape_28car_page():
    """抓取 28car 列表頁"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        print("🌐 訪問 28car 賣車列表頁...")
        page.goto('https://www.28car.com/sell_lst.php', wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(3000)
        
        # 找到內容 frame
        target_frame = None
        for frame in page.frames:
            try:
                if '28car.com' in frame.url:
                    content = frame.content()
                    if len(content) > 10000:
                        target_frame = frame
                        print(f"✅ 找到內容 frame: {frame.url[:50]}")
                        break
            except:
                continue
        
        if not target_frame:
            print("❌ 找不到內容 frame")
            browser.close()
            return
        
        # 獲取 HTML 內容
        html_content = target_frame.content()
        
        # 找到所有車盤項目（通過編號識別）
        print("\n🔍 分析網頁結構...")
        
        # 使用 Playwright 的 selector 找到所有車盤區塊
        listings = target_frame.locator('table').all()
        print(f"找到 {len(listings)} 個 table 元素")
        
        car_data = []
        
        for idx, listing in enumerate(listings[:20]):  # 只檢查前20個
            try:
                # 嘗試提取文本
                text = listing.inner_text(timeout=1000)
                
                # 檢查是否包含車盤編號（sxxxxx 格式）
                car_id_match = re.search(r'編號[：:]?\s*s(\d+)', text) or re.search(r's(\d{7})', text)
                
                if car_id_match:
                    car_id = f"s{car_id_match.group(1)}"
                    
                    # 找車型 - 通常在編號附近，包含品牌和型號
                    lines = text.split('\n')
                    model = ''
                    year = ''
                    price = ''
                    phone = ''
                    
                    for i, line in enumerate(lines):
                        line = line.strip()
                        
                        # 找車型：包含中文品牌的行
                        brands = ['奧迪', '寶馬', '平治', '豐田', '本田', '凌志', '日產', '萬事得', 
                                  '特斯拉', '保時捷', '福特', '現代', '起亞', '鈴木', '三菱',
                                  'Audi', 'BMW', 'Benz', 'Mercedes', 'Toyota', 'Honda', 'Lexus',
                                  'Nissan', 'Mazda', 'Tesla', 'Porsche', 'Ford', 'Hyundai']
                        
                        for brand in brands:
                            if brand in line and len(line) > 5 and len(line) < 80:
                                # 這可能是車型行
                                model = line
                                
                                # 嘗試提取年份（4位數字）
                                year_match = re.search(r'(20\d{2}|19\d{2})', line)
                                if year_match:
                                    year = year_match.group(1)
                                break
                        
                        # 找價格（$xx萬 格式）
                        if not price:
                            price_match = re.search(r'\$([\d.]+)萬', line)
                            if price_match:
                                price = price_match.group(0)
                        
                        # 找電話（8位數字）
                        if not phone:
                            phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', line)
                            if phone_match:
                                phone = phone_match.group(1).replace('-', '').replace(' ', '')
                    
                    if model:  # 只保存有車型的記錄
                        car_data.append({
                            'car_id': car_id,
                            'model': model[:100],
                            'year': year,
                            'price': price,
                            'phone': phone,
                            'details': text[:200]
                        })
                        
                        print(f"\n🚗 車盤 {car_id}:")
                        print(f"   車型: {model[:60]}")
                        print(f"   年份: {year}")
                        print(f"   價格: {price}")
                        print(f"   電話: {phone if phone else '未找到'}")
                        
            except Exception as e:
                continue
        
        print(f"\n✅ 總共找到 {len(car_data)} 個車盤")
        
        # 保存到資料庫
        for car in car_data:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO car_listings 
                    (car_id, model, year, price, phone, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (car['car_id'], car['model'], car['year'], car['price'], 
                      car['phone'], car['details']))
            except Exception as e:
                print(f"保存失敗 {car['car_id']}: {e}")
        
        conn.commit()
        
        # 顯示統計
        cursor.execute('SELECT COUNT(*) FROM car_listings')
        count = cursor.fetchone()[0]
        print(f"\n📊 資料庫中總計: {count} 個車盤")
        
        cursor.execute('SELECT COUNT(*) FROM car_listings WHERE phone != ""')
        phone_count = cursor.fetchone()[0]
        print(f"📞 有電話的: {phone_count} 個")
        
        browser.close()

if __name__ == "__main__":
    scrape_28car_page()
    conn.close()
    print("\n✅ 測試完成")
