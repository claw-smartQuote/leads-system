#!/usr/bin/env python3
"""
28car 簡化爬蟲測試
只抓取電話和車型
"""

from playwright.sync_api import sync_playwright
import re
import sqlite3
from pathlib import Path

db_path = Path.home() / 'Desktop/汽車保險潛客數據/test_simple.db'
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS car28_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        email TEXT,
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
    '英菲尼迪', 'Infiniti', '，吉普', 'Jeep', '富豪', 'Volvo',
    '起亞', 'Kia', 'Audi', 'BMW', 'Benz', 'Toyota', 'Honda',
]

def save_lead(phone, model):
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO car28_leads (phone, model, created_at)
            VALUES (?, ?, datetime('now'))
        ''', (phone, model))
        conn.commit()
        return True
    except:
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
        
        # 找電話
        phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', line)
        if phone_match:
            phone = phone_match.group(1).replace('-', '').replace(' ', '')
            if re.match(r'^\d{8}$', phone):
                model = ''
                
                # 向後搜索車型（行i之前的行包含車型）
                for j in range(max(0, i-1), max(0, i-25), -1):
                    check = lines[j].strip()
                    for brand in all_brands:
                        if brand in check and len(check) > 5:
                            model = check[:80].strip()
                            break
                    if model:
                        break
                
                if save_lead(phone, model):
                    count += 1
                    model_str = f" 🚗{model[:30]}" if model else ""
                    print(f"✅ {phone}{model_str}")
                    
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
    print(f"   有車型: {with_model}")
    
    browser.close()

conn.close()
