#!/usr/bin/env python3
"""
28car 爬蟲 - 寬鬆版
只要有8位電話號碼就抓取，不限定車型/來源
"""

from playwright.sync_api import sync_playwright
import re
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# 設定
TARGET_COUNT = 100
DB_PATH = Path('/Users/claw/.openclaw/workspace/car28_scraper_loose.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/28car_潛客_寬鬆版.xlsx')

# 品牌列表（用於提取車型，非過濾條件）
all_brands = [
    '奧迪', 'Audi', '寶馬', 'BMW', '平治', 'Mercedes', 'Benz', '豐田', 'Toyota', 
    '本田', 'Honda', '凌志', 'Lexus', '日產', 'Nissan', '萬事得', 'Mazda', 
    '現代', 'Hyundai', '福士', 'Volkswagen', 'VW', '福特', 'Ford', '保時捷', 'Porsche', 
    '特斯拉', 'Tesla', '迷你', 'Mini', '路虎', 'Land Rover', '積架', 'Jaguar', 
    '瑪莎拉蒂', 'Maserati', '法拉利', 'Ferrari', '林寶堅尼', 'Lamborghini', 
    '麥拿倫', 'McLaren', '勞斯萊斯', 'Rolls-Royce', '賓利', 'Bentley', 
    '蓮花', 'Lotus', '雪鐵龍', 'Citroen', '雷諾', 'Renault', '標緻', 'Peugeot',
    '鈴木', 'Suzuki', '三菱', 'Mitsubishi', '斯巴魯', 'Subaru', '英菲尼迪', 'Infiniti', 
    '吉普', 'Jeep', '富豪', 'Volvo', '起亞', 'Kia', '五十鈴', 'Isuzu', '猛獅', 'MAN',
    '日野', 'Hino', '大發', 'Daihatsu', '快意', 'Fiat', '愛快', 'Alfa Romeo',
    '雪弗蘭', 'Chevrolet', '悍馬', 'Hummer'
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS car28_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

def save_lead(cursor, conn, phone, email, model, description, source, page):
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO car28_leads (phone, email, model, description, source, page, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (phone, email, model, description, source, page, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return cursor.rowcount > 0
    except:
        return False

def extract_email(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None

def extract_model(lines, phone_idx):
    """嘗試提取車型（非必須）"""
    for j in range(max(0, phone_idx-1), max(0, phone_idx-80), -1):
        check = lines[j].strip()
        if check and len(check) > 3:
            for brand in all_brands:
                if brand in check:
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

def is_valid_phone(phone):
    """只檢查是否為8位數字"""
    if not re.match(r'^\d{8}$', phone):
        return False
    # 排除明顯的非電話號碼（如年份、價格等）
    if phone.startswith('20') and int(phone) > 20000000:  # 可能是年份2025等
        return False
    if phone.startswith('19') and int(phone) > 19900000:
        return False
    return True

def get_total_count(cursor):
    cursor.execute('SELECT COUNT(*) FROM car28_leads')
    return cursor.fetchone()[0]

def export_to_excel(cursor):
    cursor.execute('''
        SELECT phone as 電話, email as 電郵, model as 車型, 
               description as 描述, source as 來源, page as 頁碼, created_at as 創建時間
        FROM car28_leads 
        ORDER BY page, phone
    ''')
    rows = cursor.fetchall()
    
    df = pd.DataFrame(rows, columns=['電話', '電郵', '車型', '描述', '來源', '頁碼', '創建時間'])
    df.to_excel(EXCEL_PATH, index=False)
    print(f"\n📊 已導出 {len(df)} 條記錄到: {EXCEL_PATH}")
    return len(df)

def main():
    print("🚗 28car 爬蟲 - 寬鬆版 (只要有8位電話就抓)\n")
    
    conn, cursor = init_db()
    start_count = get_total_count(cursor)
    print(f"📊 數據庫現有: {start_count} 條\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        total_new = 0
        
        for page_num in range(1, 30):  # 最多30頁
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
                        
                        # 嘗試提取車型（非必須）
                        model = extract_model(lines, i)
                        email = extract_email('\n'.join(lines[max(0,i-30):i+30]))
                        description = extract_description(lines, i)
                        source = f"page_{page_num}_line_{i}"
                        
                        if save_lead(cursor, conn, phone, email, model, description, source, page_num):
                            total_new += 1
                            page_new += 1
                            model_str = model[:30] if model else "(無車型)"
                            print(f"    ✅ {phone} | {model_str}")
                            
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
    
    # 統計
    final_count = get_total_count(cursor)
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE model != "" AND model IS NOT NULL')
    with_model = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE email IS NOT NULL')
    with_email = cursor.fetchone()[0]
    
    print(f"\n{'='*50}")
    print(f"✅ 爬蟲完成！")
    print(f"{'='*50}")
    print(f"本次新增: {total_new} 條")
    print(f"數據庫總計: {final_count} 條")
    print(f"有車型: {with_model} 條 ({100*with_model//max(1,final_count)}%)")
    print(f"有電郵: {with_email} 條 ({100*with_email//max(1,final_count)}%)")
    
    # 導出Excel
    export_to_excel(cursor)
    
    conn.close()
    print(f"\n💾 數據庫: {DB_PATH}")

if __name__ == '__main__':
    main()
