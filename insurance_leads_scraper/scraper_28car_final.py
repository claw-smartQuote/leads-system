#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
28car.com 汽車保險潛客爬蟲 - 有頭模式版本
數據自動保存到桌面 Excel 文件
"""

import os
import re
import time
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ============ 配置 ============
DESKTOP_DIR = Path.home() / "Desktop"
DATA_FOLDER = DESKTOP_DIR / "汽車保險潛客數據"
DATA_FOLDER.mkdir(exist_ok=True)

DB_PATH = DATA_FOLDER / "leads_database.db"
EXCEL_PATH = DATA_FOLDER / f"保險潛客數據_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

print(f"📂 數據保存位置: {DATA_FOLDER}")
print(f"📊 Excel 文件: {EXCEL_PATH}")

# ============ 數據庫 ============
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
            scrape_date TEXT
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

def save_lead(car_model, price, phone, seller_name, post_url, post_id, seller_type):
    """保存線索到數據庫"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO car_leads (post_id, phone, car_model, price, seller_name, post_url, seller_type, scrape_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (post_id, phone, car_model, price, seller_name, post_url, seller_type, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_leads():
    """獲取所有線索"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM car_leads ORDER BY scrape_date DESC", conn)
    conn.close()
    return df

# ============ Excel 導出 ============
def export_to_excel():
    """導出數據到 Excel"""
    df = get_all_leads()
    
    if df.empty:
        print("⚠️ 沒有數據可導出")
        return None
    
    # 重命名列為中文
    column_names = {
        'car_model': '車輛型號',
        'price': '售價',
        'seller_name': '聯絡人',
        'phone': '電話號碼',
        'seller_type': '賣家類型',
        'post_url': '帖子鏈接',
        'post_id': '帖子ID',
        'scrape_date': '抓取日期'
    }
    df = df.rename(columns=column_names)
    
    # 選擇要導出的列
    columns = ['車輛型號', '售價', '聯絡人', '電話號碼', '賣家類型', '帖子鏈接', '帖子ID', '抓取日期']
    df = df[[col for col in columns if col in df.columns]]
    
    # 保存到 Excel
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='28Car_Leads')
        
        # 調整列寬
        worksheet = writer.sheets['28Car_Leads']
        worksheet.column_dimensions['A'].width = 30  # 車輛型號
        worksheet.column_dimensions['B'].width = 15  # 售價
        worksheet.column_dimensions['C'].width = 15  # 聯絡人
        worksheet.column_dimensions['D'].width = 15  # 電話
        worksheet.column_dimensions['E'].width = 12  # 類型
        worksheet.column_dimensions['F'].width = 50  # 鏈接
        worksheet.column_dimensions['G'].width = 12  # ID
        worksheet.column_dimensions['H'].width = 12  # 日期
    
    print(f"✅ Excel 已保存: {EXCEL_PATH}")
    return EXCEL_PATH

# ============ 爬蟲 ============
def scrape_28car(max_pages=5, target_leads=20):
    """爬取 28car.com"""
    print("\n" + "="*60)
    print("🚗 28car.com 汽車保險潛客爬蟲")
    print("="*60)
    print(f"🎯 目標: {target_leads} 條線索")
    print(f"📄 最大頁數: {max_pages}")
    print("⚠️  請勿關閉彈出的瀏覽器窗口！")
    print("="*60 + "\n")
    
    init_db()
    leads_count = 0
    
    with sync_playwright() as p:
        # 使用有頭模式（會彈出瀏覽器）
        print("🌐 啟動瀏覽器...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            for page_num in range(1, max_pages + 1):
                if leads_count >= target_leads:
                    print(f"\n✅ 已達到目標 {target_leads} 條，提前結束")
                    break
                
                print(f"\n📄 處理第 {page_num}/{max_pages} 頁...")
                
                # 構建 URL
                url = f"https://www.28car.com/sell_lst.php"
                if page_num > 1:
                    url += f"?pg={page_num}"
                
                # 訪問頁面
                print(f"   載入: {url}")
                page.goto(url, wait_until='networkidle', timeout=60000)
                time.sleep(5)  # 等待 iframe 載入
                
                # 找到內容 frame
                target_frame = None
                for frame in page.frames:
                    frame_url = frame.url
                    # Frame 1 URL 是類似 https://dj1jklak2e.28car.com/sell_lst.php
                    if 'sell_lst' in frame_url and '28car.com' in frame_url and frame_url != url:
                        try:
                            html = frame.content()
                            if len(html) > 100000:
                                target_frame = frame
                                print(f"   ✅ 找到內容 iframe ({len(html)} bytes)")
                                break
                        except:
                            pass
                
                if not target_frame:
                    print(f"   ⚠️ 未找到內容，跳過")
                    continue
                
                # 獲取表格行
                rows = target_frame.query_selector_all('tr')
                print(f"   找到 {len(rows)} 行數據")
                
                page_leads = 0
                for i, row in enumerate(rows):
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
                        
                        # 跳過非車輛鏈接（如登錄頁）
                        if 'login' in detail_url or 'mbr_' in detail_url:
                            continue
                        
                        # 過濾無效數據
                        if not car_model or len(car_model) < 3:
                            continue
                        
                        # 獲取描述（包含電話）
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
                        phone_match = re.search(r'\d{4}[\s-]?\d{4}', desc_text)
                        if not phone_match:
                            continue
                            
                        phone = phone_match.group().replace('-', '').replace(' ', '')
                        
                        # 提取帖子 ID
                        post_id = ''
                        if detail_url:
                            vid_match = re.search(r'h_vid=(\d+)', detail_url)
                            post_id = vid_match.group(1) if vid_match else ''
                        
                        # 構建完整 URL
                        if detail_url and not detail_url.startswith('http'):
                            detail_url = 'https://www.28car.com/' + detail_url.lstrip('/')
                        
                        # 跳過重複
                        if is_duplicate(post_id, phone):
                            continue
                        
                        # 保存
                        if save_lead(car_model, price_text, phone, '', detail_url, post_id, '私人'):
                            leads_count += 1
                            page_leads += 1
                            print(f"   ✅ [{leads_count}] {car_model[:30]}... - {phone}")
                            
                            if leads_count >= target_leads:
                                break
                        
                    except Exception as e:
                        continue
                
                print(f"   📊 第 {page_num} 頁完成: {page_leads} 條")
                time.sleep(2)
                
        finally:
            print("\n🔒 關閉瀏覽器...")
            browser.close()
    
    # 導出 Excel
    print(f"\n{'='*60}")
    print(f"📊 爬蟲完成！")
    print(f"   總共獲取: {leads_count} 條新線索")
    
    if leads_count > 0:
        export_to_excel()
    
    print(f"{'='*60}")
    return leads_count

# ============ 主程序 ============
if __name__ == "__main__":
    import sys
    
    # 獲取命令行參數
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    # 運行爬蟲
    scrape_28car(max_pages=max_pages, target_leads=target)
