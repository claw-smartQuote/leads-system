#!/usr/bin/env python3
"""
28car 爬蟲 - 翻頁版 (目標100條)
支持多頁面抓取，直到達到目標數量
"""

from playwright.sync_api import sync_playwright
import re
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# 設定
TARGET_COUNT = 100  # 目標數量
DB_PATH = Path('/Users/claw/.openclaw/workspace/car28_scraper.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/28car_潛客_100條.xlsx')

# 品牌列表
all_brands = [
    '奧迪', 'Audi', '寶馬', 'BMW', '平治', 'Mercedes', 'Benz', '豐田', 'Toyota', 
    '本田', 'Honda', '凌志', 'Lexus', '日產', 'Nissan', '萬事得', 'Mazda', 
    '現代', 'Hyundai', '福士', 'Volkswagen', 'VW', '福特', 'Ford', '保時捷', 'Porsche', 
    '特斯拉', 'Tesla', '迷你', 'Mini', '路虎', 'Land Rover', '積架', 'Jaguar', 
    '瑪莎拉蒂', 'Maserati', '法拉利', 'Ferrari', '林寶堅尼', 'Lamborghini', 
    '麥拿倫', 'McLaren', '勞斯萊斯', 'Rolls-Royce', '賓利', 'Bentley', 
    '蓮花', 'Lotus', '雪鐵龍', 'Citroen', '雷諾', 'Renault', '標緻', 'Peugeot',
    '鈴木', 'Suzuki', '三菱', 'Mitsubishi', '斯巴魯', 'Subaru', '英菲尼迪', 'Infiniti', 
    '吉普', 'Jeep', '富豪', 'Volvo', '起亞', 'Kia', '猛獅', 'MAN', '五十鈴', 'Isuzu',
    '快意', 'Fiat', '愛快', 'Alfa Romeo', '雪弗蘭', 'Chevrolet', '悍馬', 'Hummer',
    '胡士托', 'Hustler', '大發', 'Daihatsu', '日野', 'Hino'
]

car_keywords = ['汽油', '柴油', '電動', '混能', '油電', 'cc', '自動', '棍', '座', '輛', '偈', '裡數', 'km', '公里']

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
    except Exception as e:
        print(f"  保存失敗: {e}")
        return False

def extract_email(text):
    """提取電郵地址"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0)
    return None

def is_valid_phone(phone, context_lines, current_idx):
    """檢查是否為有效的汽車電話號碼"""
    if not re.match(r'^\d{8}$', phone):
        return False
    
    # 常見的非車主電話前綴（排除經銷商）
    dealer_prefixes = ['3188', '3698', '3760', '2880', '2830', '3100', '2150', '2300']
    if any(phone.startswith(p) for p in dealer_prefixes):
        return False
    
    search_start = max(0, current_idx - 40)
    search_end = min(len(context_lines), current_idx + 40)
    nearby_text = ' '.join(context_lines[search_start:search_end])
    
    # 檢查品牌
    for brand in all_brands:
        if brand in nearby_text:
            return True
    
    # 檢查年份
    if re.search(r'20\d{2}|19\d{2}', nearby_text):
        return True
    
    # 檢查汽車關鍵詞
    for keyword in car_keywords:
        if keyword in nearby_text:
            return True
    
    return False

def extract_model(lines, phone_idx):
    """從電話附近提取車型"""
    # 向前搜索
    for j in range(max(0, phone_idx-1), max(0, phone_idx-50), -1):
        check = lines[j].strip()
        if check and len(check) > 3:
            for brand in all_brands:
                if brand in check:
                    # 清理車型文字
                    model = check.replace('\t', ' ').replace('  ', ' ')[:80].strip()
                    return model
    return ''

def extract_description(lines, phone_idx):
    """提取車輛描述"""
    desc_parts = []
    for j in range(max(0, phone_idx-10), min(len(lines), phone_idx+10)):
        line = lines[j].strip()
        if line and len(line) > 10 and '電話' not in line and '查詢' not in line:
            desc_parts.append(line)
    return ' | '.join(desc_parts[:3])[:200]

def scrape_page(page, page_num, cursor, conn):
    """抓取單個頁面"""
    new_count = 0
    
    # 找到內容 frame
    target_frame = None
    for frame in page.frames:
        if '28car.com' in frame.url:
            try:
                text = frame.inner_text('body', timeout=5000)
                if len(text) > 20000:
                    target_frame = frame
                    break
            except:
                continue
    
    if not target_frame:
        print(f"  ⚠️ 第{page_num}頁找不到內容")
        return 0
    
    text = target_frame.inner_text('body')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    print(f"  📄 第{page_num}頁: {len(lines)} 行文字")
    
    for i, line in enumerate(lines):
        # 找8位數電話
        phones = re.findall(r'(\d{8})', line)
        
        for phone in phones:
            if not is_valid_phone(phone, lines, i):
                continue
            
            # 提取信息
            model = extract_model(lines, i)
            email = extract_email('\n'.join(lines[max(0,i-20):i+20]))
            description = extract_description(lines, i)
            source = f"page_{page_num}_line_{i}"
            
            if save_lead(cursor, conn, phone, email, model, description, source, page_num):
                new_count += 1
                model_str = model[:35] if model else "(無車型)"
                print(f"  ✅ {phone} | {model_str}")
                
                if get_total_count(cursor) >= TARGET_COUNT:
                    return new_count
    
    return new_count

def get_total_count(cursor):
    cursor.execute('SELECT COUNT(*) FROM car28_leads')
    return cursor.fetchone()[0]

def export_to_excel(cursor):
    """導出到Excel"""
    cursor.execute('''
        SELECT phone as 電話, email as 電郵, model as 車型, 
               description as 描述, source as 來源, created_at as 創建時間
        FROM car28_leads 
        ORDER BY created_at DESC
    ''')
    rows = cursor.fetchall()
    
    df = pd.DataFrame(rows, columns=['電話', '電郵', '車型', '描述', '來源', '創建時間'])
    df.to_excel(EXCEL_PATH, index=False)
    print(f"\n📊 已導出 {len(df)} 條記錄到: {EXCEL_PATH}")
    return len(df)

def main():
    print("🚗 28car 爬蟲啟動 (目標100條)\n")
    
    conn, cursor = init_db()
    start_count = get_total_count(cursor)
    print(f"📊 數據庫現有: {start_count} 條\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        # 訪問首頁
        print("🌐 訪問 28car...")
        page.goto('https://www.28car.com/sell_lst.php', wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(3000)
        
        page_num = 1
        total_new = 0
        
        while get_total_count(cursor) < TARGET_COUNT and page_num <= 20:
            print(f"\n📄 正在抓取第 {page_num} 頁...")
            
            new_in_page = scrape_page(page, page_num, cursor, conn)
            total_new += new_in_page
            
            current_total = get_total_count(cursor)
            print(f"   本頁新增: {new_in_page} | 累計: {current_total}/{TARGET_COUNT}")
            
            if current_total >= TARGET_COUNT:
                print(f"\n🎉 已達到目標 {TARGET_COUNT} 條！")
                break
            
            # 尋找下一頁按鈕
            try:
                next_found = False
                for frame in page.frames:
                    if '28car.com' in frame.url:
                        try:
                            # 嘗試多種方式找下一頁
                            next_selectors = [
                                'a:has-text("下一頁")',
                                'a:has-text("Next")',
                                'a[title="下一頁"]',
                                'a:has(> img[alt="下一頁"])',
                            ]
                            for selector in next_selectors:
                                try:
                                    next_btn = frame.locator(selector).first
                                    if next_btn.count() > 0 and next_btn.is_visible():
                                        next_btn.click()
                                        page.wait_for_timeout(3000)
                                        next_found = True
                                        break
                                except:
                                    continue
                            if next_found:
                                break
                        except:
                            continue
                
                if not next_found:
                    print("\n⚠️ 沒有更多頁面了")
                    break
                    
            except Exception as e:
                print(f"\n⚠️ 翻頁失敗: {e}")
                break
            
            page_num += 1
        
        browser.close()
    
    # 統計
    final_count = get_total_count(cursor)
    cursor.execute('SELECT COUNT(*) FROM car28_leads WHERE model != "" AND model IS NOT NULL')
    with_model = cursor.fetchone()[0]
    
    print(f"\n{'='*50}")
    print(f"✅ 爬蟲完成！")
    print(f"{'='*50}")
    print(f"本次新增: {total_new} 條")
    print(f"數據庫總計: {final_count} 條")
    print(f"有車型資料: {with_model} 條 ({100*with_model//max(1,final_count)}%)")
    
    # 導出Excel
    export_to_excel(cursor)
    
    conn.close()
    print(f"\n💾 數據庫保存於: {DB_PATH}")

if __name__ == '__main__':
    main()
