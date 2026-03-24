#!/usr/bin/env python3
"""
28car 爬蟲 - 完整版 v3
功能：
- 只要有8位電話號碼就抓取
- 自動提取車廠名稱（從車型中識別）
- 目標100條
"""

from playwright.sync_api import sync_playwright
import re
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# 設定
TARGET_COUNT = 100
DB_PATH = Path('/Users/claw/.openclaw/workspace/car28_scraper_v3.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/28car_潛客_完整版_v3.xlsx')

# 品牌列表（中文優先，用於識別車廠）
BRANDS = [
    ('豐田', 'Toyota'), ('Toyota', 'Toyota'),
    ('寶馬', 'BMW'), ('BMW', 'BMW'),
    ('平治', 'Mercedes'), ('Mercedes', 'Mercedes'), ('Benz', 'Mercedes'),
    ('本田', 'Honda'), ('Honda', 'Honda'),
    ('凌志', 'Lexus'), ('Lexus', 'Lexus'),
    ('日產', 'Nissan'), ('Nissan', 'Nissan'),
    ('萬事得', 'Mazda'), ('Mazda', 'Mazda'),
    ('現代', 'Hyundai'), ('Hyundai', 'Hyundai'),
    ('福士', 'Volkswagen'), ('Volkswagen', 'Volkswagen'), ('VW', 'Volkswagen'),
    ('福特', 'Ford'), ('Ford', 'Ford'),
    ('保時捷', 'Porsche'), ('Porsche', 'Porsche'),
    ('特斯拉', 'Tesla'), ('Tesla', 'Tesla'),
    ('迷你', 'Mini'), ('Mini', 'Mini'),
    ('路虎', 'Land Rover'), ('Land Rover', 'Land Rover'),
    ('積架', 'Jaguar'), ('Jaguar', 'Jaguar'),
    ('瑪莎拉蒂', 'Maserati'), ('Maserati', 'Maserati'),
    ('法拉利', 'Ferrari'), ('Ferrari', 'Ferrari'),
    ('林寶堅尼', 'Lamborghini'), ('Lamborghini', 'Lamborghini'),
    ('麥拿倫', 'McLaren'), ('McLaren', 'McLaren'),
    ('勞斯萊斯', 'Rolls-Royce'), ('Rolls-Royce', 'Rolls-Royce'),
    ('賓利', 'Bentley'), ('Bentley', 'Bentley'),
    ('蓮花', 'Lotus'), ('Lotus', 'Lotus'),
    ('雪鐵龍', 'Citroen'), ('Citroen', 'Citroen'),
    ('雷諾', 'Renault'), ('Renault', 'Renault'),
    ('標緻', 'Peugeot'), ('Peugeot', 'Peugeot'),
    ('鈴木', 'Suzuki'), ('Suzuki', 'Suzuki'),
    ('三菱', 'Mitsubishi'), ('Mitsubishi', 'Mitsubishi'),
    ('斯巴魯', 'Subaru'), ('Subaru', 'Subaru'),
    ('英菲尼迪', 'Infiniti'), ('Infiniti', 'Infiniti'),
    ('吉普', 'Jeep'), ('Jeep', 'Jeep'),
    ('富豪', 'Volvo'), ('Volvo', 'Volvo'),
    ('起亞', 'Kia'), ('Kia', 'Kia'),
    ('五十鈴', 'Isuzu'), ('Isuzu', 'Isuzu'),
    ('日野', 'Hino'), ('Hino', 'Hino'),
    ('大發', 'Daihatsu'), ('Daihatsu', 'Daihatsu'),
    ('快意', 'Fiat'), ('Fiat', 'Fiat'),
    ('愛快', 'Alfa Romeo'), ('Alfa Romeo', 'Alfa Romeo'),
    ('雪弗蘭', 'Chevrolet'), ('Chevrolet', 'Chevrolet'),
    ('悍馬', 'Hummer'), ('Hummer', 'Hummer'),
    ('猛獅', 'MAN'), ('MAN', 'MAN'),
    ('奧迪', 'Audi'), ('Audi', 'Audi'),
]

def init_db():
    """初始化數據庫"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS car28_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT,
            phone TEXT UNIQUE,
            email TEXT,
            model TEXT,
            description TEXT,
            source TEXT,
            page INTEGER,
            created_at TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def extract_brand(model_text):
    """從車型文字中提取車廠名稱"""
    if not model_text:
        return ''
    # 優先匹配中文品牌（通常在前面）
    for cn_name, en_name in BRANDS:
        if cn_name in model_text:
            return cn_name
    # 再匹配英文品牌
    for cn_name, en_name in BRANDS:
        if en_name in model_text:
            return en_name
    return ''

def extract_model(lines, phone_idx):
    """嘗試提取車型（從電話附近搜索）"""
    for j in range(max(0, phone_idx-1), max(0, phone_idx-80), -1):
        check = lines[j].strip()
        if check and len(check) > 3:
            for cn_name, en_name in BRANDS:
                if cn_name in check or en_name in check:
                    return check.replace('\t', ' ').replace('  ', ' ')[:100].strip()
    return ''

def extract_description(lines, phone_idx):
    """提取附近文字作為描述"""
    desc_parts = []
    for j in range(max(0, phone_idx-20), min(len(lines), phone_idx+20)):
        line = lines[j].strip()
        if line and len(line) > 5:
            desc_parts.append(line)
    return ' | '.join(desc_parts[:5])[:300]

def extract_email(text):
    """提取電郵地址"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None

def is_valid_phone(phone):
    """只檢查是否為8位數字"""
    if not re.match(r'^\d{8}$', phone):
        return False
    # 排除明顯的非電話號碼（如年份）
    if phone.startswith('20') and int(phone) > 20000000:
        return False
    if phone.startswith('19') and int(phone) > 19900000:
        return False
    return True

def save_lead(cursor, conn, brand, phone, email, model, description, source, page):
    """保存潛客資料"""
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO car28_leads (brand, phone, email, model, description, source, page, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (brand, phone, email, model, description, source, page, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return cursor.rowcount > 0
    except:
        return False

def get_total_count(cursor):
    cursor.execute('SELECT COUNT(*) FROM car28_leads')
    return cursor.fetchone()[0]

def export_to_excel(cursor):
    """導出到Excel"""
    cursor.execute('''
        SELECT brand as 車廠, phone as 電話, email as 電郵, model as 車型, 
               description as 描述, source as 來源, page as 頁碼, created_at as 創建時間
        FROM car28_leads 
        ORDER BY brand, phone
    ''')
    rows = cursor.fetchall()
    
    df = pd.DataFrame(rows, columns=['車廠', '電話', '電郵', '車型', '描述', '來源', '頁碼', '創建時間'])
    df.to_excel(EXCEL_PATH, index=False)
    return len(df)

def main():
    print("="*60)
    print("🚗 28car 爬蟲 - 完整版 v3")
    print("="*60)
    print("功能：寬鬆條件(有電話就抓) + 自動提取車廠 + 目標100條\n")
    
    # 初始化
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("🗑️  清除舊數據庫")
    
    conn, cursor = init_db()
    print(f"✅ 數據庫初始化完成\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        total_new = 0
        
        # 遍歷頁面
        for page_num in range(1, 30):
            if get_total_count(cursor) >= TARGET_COUNT:
                break
                
            url = f'https://www.28car.com/sell_lst.php?h_page={page_num}' if page_num > 1 else 'https://www.28car.com/sell_lst.php'
            print(f"📄 第 {page_num} 頁...")
            
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(4000)
                
                # 找到內容 frame
                target_frame = None
                for frame in page.frames:
                    if '28car.com' in frame.url:
                        try:
                            text = frame.inner_text('body', timeout=5000)
                            if len(text) > 15000:
                                target_frame = frame
                                break
                        except:
                            continue
                
                if not target_frame:
                    print(f"   ⚠️ 無內容，停止")
                    break
                
                text = target_frame.inner_text('body')
                if '電話' not in text or len(text) < 10000:
                    print(f"   ⚠️ 無有效內容，停止")
                    break
                
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                seen_phones = set()
                page_new = 0
                
                for i, line in enumerate(lines):
                    # 找所有8位數字
                    phones = re.findall(r'(\d{8})', line)
                    
                    for phone in phones:
                        if phone in seen_phones:
                            continue
                        if not is_valid_phone(phone):
                            continue
                        
                        seen_phones.add(phone)
                        
                        # 提取信息
                        model = extract_model(lines, i)
                        brand = extract_brand(model)
                        email = extract_email('\n'.join(lines[max(0,i-30):i+30]))
                        description = extract_description(lines, i)
                        source = f"page_{page_num}_line_{i}"
                        
                        if save_lead(cursor, conn, brand, phone, email, model, description, source, page_num):
                            total_new += 1
                            page_new += 1
                            brand_str = brand if brand else "(未識別)"
                            model_str = model[:25] if model else "(無)"
                            print(f"    ✅ {phone} | {brand_str} | {model_str}")
                            
                            if get_total_count(cursor) >= TARGET_COUNT:
                                break
                    
                    if get_total_count(cursor) >= TARGET_COUNT:
                        break
                
                current_total = get_total_count(cursor)
                print(f"   本頁新增: {page_new} | 累計: {current_total}/{TARGET_COUNT}\n")
                    
            except Exception as e:
                print(f"   ❌ 錯誤: {e}")
                continue
        
        browser.close()
    
    # 統計報告
    final_count = get_total_count(cursor)
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE brand != "" AND brand IS NOT NULL')
    with_brand = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE model != "" AND model IS NOT NULL')
    with_model = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE email IS NOT NULL')
    with_email = cursor.fetchone()[0]
    
    print("="*60)
    print("✅ 爬蟲完成！")
    print("="*60)
    print(f"📊 統計：")
    print(f"   總數：{final_count} 條")
    print(f"   有車廠：{with_brand} 條 ({100*with_brand//max(1,final_count)}%)")
    print(f"   有車型：{with_model} 條 ({100*with_model//max(1,final_count)}%)")
    print(f"   有電郵：{with_email} 條 ({100*with_email//max(1,final_count)}%)")
    
    print(f"\n🏭 車廠分布：")
    cursor.execute('SELECT brand, COUNT(*) FROM car28_leads WHERE brand IS NOT NULL GROUP BY brand ORDER BY COUNT(*) DESC')
    for brand, cnt in cursor.fetchall():
        print(f"   {brand}: {cnt}條")
    
    # 導出Excel
    export_to_excel(cursor)
    print(f"\n📁 Excel導出: {EXCEL_PATH}")
    print(f"💾 數據庫: {DB_PATH}")
    
    conn.close()

if __name__ == '__main__':
    main()
