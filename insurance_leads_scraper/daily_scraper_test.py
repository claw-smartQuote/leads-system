#!/usr/bin/env python3
"""
28car 完整爬蟲測試 - 優化版
"""

from playwright.sync_api import sync_playwright
import re
import sqlite3
from pathlib import Path

db_path = Path.home() / 'Desktop/汽車保險潛客數據/test_v2.db'
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS car28_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        model TEXT,
        source TEXT,
        created_at TEXT
    )
''')
conn.commit()

# 品牌列表
all_brands = [
    '奧迪', '寶馬', '平治', 'Mercedes', '豐田', 'Toyota', '本田', 'Honda', '凌志', 'Lexus',
    '日產', 'Nissan', '萬事得', 'Mazda', '現代', 'Hyundai', '福士', 'Volkswagen',
    '福特', 'Ford', '保時捷', 'Porsche', '特斯拉', 'Tesla', '迷你', 'Mini',
    '路虎', 'Land Rover', '積架', 'Jaguar', '瑪莎拉蒂', 'Maserati',
    '法拉利', 'Ferrari', '林寶堅尼', 'Lamborghini', '麥拿倫', 'McLaren',
    '勞斯萊斯', 'Rolls-Royce', '賓利', 'Bentley', '蓮花', 'Lotus',
    '雪鐵龍', 'Citroen', '雷諾', 'Renault', '標緻', 'Peugeot',
    '鈴木', 'Suzuki', '三菱', 'Mitsubishi', '斯巴魯', 'Subaru',
    '英菲尼迪', 'Infiniti', '吉普', 'Jeep', '富豪', 'Volvo',
    '起亞', 'Kia', 'Audi', 'BMW', 'Benz', 'Toyota', 'Honda',
]

def save_lead(phone, model):
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO car28_leads (phone, model, created_at)
            VALUES (?, ?, datetime('now'))
        ''', (phone, model))
        conn.commit()
        return cursor.rowcount > 0
    except:
        return False

def is_valid_phone(phone, context_lines, current_idx):
    """檢查是否為有效的汽車電話號碼"""
    # 必須是8位數字
    if not re.match(r'^\d{8}$', phone):
        return False
    
    # 檢查附近是否有品牌名稱（說明這是汽車相關電話）
    search_start = max(0, current_idx - 30)
    search_end = min(len(context_lines), current_idx + 30)
    nearby_text = ' '.join(context_lines[search_start:search_end])
    
    # 如果附近有品牌，則是有效的
    for brand in all_brands:
        if brand in nearby_text:
            return True
    
    # 如果附近有年份（20xx），說明是汽車詳情頁的電話
    if re.search(r'20\d{2}|19\d{2}', nearby_text):
        return True
    
    # 如果附近有汽車相關詞彙
    car_keywords = ['汽油', '柴油', '電動', '混能', 'cc', '自動', '棍', '座', '輛']
    for keyword in car_keywords:
        if keyword in nearby_text:
            return True
    
    return False

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    
    print("🌐 訪問 28car...")
    page.goto('https://www.28car.com/sell_lst.php', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(3000)
    
    # 找到內容 frame
    target_frame = None
    for frame in page.frames:
        if '28car.com' in frame.url:
            try:
                text = frame.inner_text('body', timeout=2000)
                if len(text) > 30000:
                    target_frame = frame
                    print(f"✅ 找到 frame: {len(text)} 字符")
                    break
            except:
                continue
    
    if not target_frame:
        print("❌ 找不到內容 frame")
        browser.close()
        exit(1)
    
    text = target_frame.inner_text('body')
    lines = text.split('\n')
    
    print(f"📄 總共 {len(lines)} 行文字")
    
    count = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 找8位數字
        phone_match = re.search(r'(\d{8})', line)
        if phone_match:
            phone = phone_match.group(1)
            
            # 驗證是否為有效的汽車電話
            if is_valid_phone(phone, lines, i):
                model = ''
                
                # 向後搜索車型
                for j in range(max(0, i-1), max(0, i-30), -1):
                    check = lines[j].strip()
                    if check and len(check) > 3:
                        for brand in all_brands:
                            if brand in check:
                                model = check[:80].strip()
                                break
                    if model:
                        break
                
                if save_lead(phone, model):
                    count += 1
                    model_str = f" 🚗{model[:35]}" if model else " 🚗(無車型)"
                    print(f"✅ {count:3d}. {phone}{model_str}")
                    
                    if count >= 100:
                        break
    
    print(f"\n✅ 完成！總共抓取 {count} 條記錄")
    
    # 顯示統計
    cursor.execute('SELECT COUNT(*) FROM car28_leads')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE model != ""')
    with_model = cursor.fetchone()[0]
    print(f"\n📊 統計：")
    print(f"   總記錄: {total}")
    print(f"   有車型: {with_model} ({100*with_model//max(1,total)}%)")
    
    browser.close()

conn.close()
