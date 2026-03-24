#!/usr/bin/env python3
"""
28car.com 電話提取腳本 - 終極版本
使用 JavaScript 直接從頁面提取數據
"""

import time
import re
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# 路徑設置
DATA_DIR = Path.home() / "Desktop" / "汽車保險潛客數據"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "leads.db"
EXCEL_PATH = DATA_DIR / f"潛客數據_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY, post_id TEXT UNIQUE, phone TEXT UNIQUE,
        car_model TEXT, price TEXT, url TEXT, date TEXT)''')
    conn.commit()
    conn.close()

def save_lead(post_id, phone, car_model, price, url):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO leads VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                  (post_id, phone, car_model, price, url, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return c.rowcount > 0
    except:
        return False

def export_excel():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT car_model 車型, price 價格, phone 電話, url 鏈接, date 日期 FROM leads", conn)
    conn.close()
    if not df.empty:
        df.to_excel(EXCEL_PATH, index=False)
        print(f"\n📊 Excel 已保存: {EXCEL_PATH}")
        print(f"   共 {len(df)} 條記錄")
    return df

def extract_from_28car(max_pages=3):
    print("=" * 60)
    print("🚗 28car.com 電話提取")
    print("=" * 60)
    print("⚠️  請勿關閉瀏覽器窗口！\n")
    
    init_db()
    total = 0
    
    with sync_playwright() as p:
        # 啟動有頭瀏覽器
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            for pg in range(1, max_pages + 1):
                print(f"\n📄 正在處理第 {pg} 頁...")
                
                # 訪問頁面
                url = f"https://www.28car.com/sell_lst.php" + (f"?pg={pg}" if pg > 1 else "")
                page.goto(url, wait_until='networkidle', timeout=60000)
                time.sleep(8)  # 等待 iframe 載入
                
                # 使用 JavaScript 直接從 frame 中提取數據
                result = page.evaluate("""() => {
                    const data = [];
                    
                    // 遍歷所有 frames 找到包含車輛信息的
                    const allFrames = Array.from(window.frames);
                    for (const frame of allFrames) {
                        try {
                            const doc = frame.document;
                            if (!doc || !doc.body) continue;
                            
                            // 查找所有包含 sell_dsp 的鏈接
                            const links = doc.querySelectorAll('a[href*="sell_dsp.php"]');
                            
                            for (const link of links) {
                                const href = link.getAttribute('href');
                                const vidMatch = href.match(/h_vid=(\\d+)/);
                                if (!vidMatch) continue;
                                
                                const vid = vidMatch[1];
                                const carModel = link.innerText.trim();
                                
                                // 跳過無效的
                                if (!carModel || carModel.length < 3 || carModel.includes('$')) continue;
                                
                                // 在父元素中查找電話
                                let phone = '';
                                let price = '';
                                
                                // 向上查找行
                                let row = link.closest('tr') || link.parentElement?.closest('tr');
                                if (row) {
                                    const rowText = row.innerText;
                                    
                                    // 提取電話 (8位數字)
                                    const phoneMatch = rowText.match(/(\\d{4}[\\s\\-]?\\d{4})/);
                                    if (phoneMatch) {
                                        phone = phoneMatch[1].replace(/[\\s\\-]/g, '');
                                    }
                                    
                                    // 提取價格
                                    const priceMatch = rowText.match(/(HK\\$[\\d,]+)/);
                                    if (priceMatch) {
                                        price = priceMatch[1];
                                    }
                                }
                                
                                if (phone && carModel) {
                                    data.push({
                                        vid: vid,
                                        model: carModel,
                                        phone: phone,
                                        price: price,
                                        url: 'https://www.28car.com/sell_dsp.php?h_vid=' + vid
                                    });
                                }
                            }
                        } catch (e) {}
                    }
                    
                    return data;
                }""")
                
                if result and len(result) > 0:
                    print(f"   找到 {len(result)} 個潛在數據")
                    
                    saved = 0
                    for item in result:
                        if save_lead(item['vid'], item['phone'], item['model'], item['price'], item['url']):
                            total += 1
                            saved += 1
                            print(f"   ✅ [{total}] {item['model'][:30]} - {item['phone']}")
                    
                    print(f"   💾 本頁新保存: {saved} 條")
                else:
                    print(f"   ⚠️ 本頁未找到數據")
                
                time.sleep(3)
                
        finally:
            print("\n🔒 關閉瀏覽器...")
            browser.close()
    
    # 導出結果
    print(f"\n{'=' * 60}")
    print(f"✅ 總共獲取: {total} 條新線索")
    export_excel()
    print(f"📁 數據位置: {DATA_DIR}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    import sys
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    extract_from_28car(max_pages=pages)
