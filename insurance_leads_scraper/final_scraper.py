#!/usr/bin/env python3
"""
28car.com 爬蟲 - 終極版本
直接獲取頁面所有文本並提取電話
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

def scrape():
    print("=" * 60)
    print("🚗 28car.com 爬蟲")
    print("=" * 60)
    print("⚠️ 請勿關閉瀏覽器窗口！\n")
    
    leads = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            # 訪問頁面
            print("📄 載入頁面...")
            page.goto("https://www.28car.com/sell_lst.php", timeout=60000)
            time.sleep(12)  # 等待 JS 加載
            
            # 獲取所有 frames 的內容
            print("🔍 分析頁面內容...")
            
            for i, frame in enumerate(page.frames):
                try:
                    url = frame.url
                    if '28car.com' not in url:
                        continue
                    
                    # 獲取文本
                    text = frame.inner_text('body', timeout=5000)
                    
                    if len(text) < 1000:
                        continue
                    
                    print(f"\n  Frame {i}: {len(text)} 字符")
                    
                    # 提取所有 8位數字（電話）
                    phones = re.findall(r'\b(\d{4}[\s\-]?\d{4})\b', text)
                    phones = [p.replace('-', '').replace(' ', '') for p in phones]
                    phones = list(set(phones))  # 去重
                    
                    # 提取電郵
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    emails = list(set(emails))
                    
                    print(f"    找到 {len(phones)} 個電話, {len(emails)} 個電郵")
                    if phones[:3]:
                        print(f"    電話示例: {phones[:3]}")
                    if emails[:3]:
                        print(f"    電郵示例: {emails[:3]}")
                    
                    # 提取車型（通過 sell_dsp 鏈接周圍的文本）
                    html = frame.content()
                    
                    # 查找模式: sell_dsp.php?h_vid=數字 周圍的車型名稱
                    # 這是一個簡化的模式匹配
                    lines = text.split('\n')
                    for j, line in enumerate(lines):
                        # 找包含電話的行
                        phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', line)
                        if phone_match:
                            phone = phone_match.group(1).replace('-', '').replace(' ', '')
                            
                            # 在周圍幾行找車型
                            context = ' '.join(lines[max(0,j-3):min(len(lines),j+3)])
                            
                            # 簡單提取可能的車型（包含字母和數字的詞）
                            model_match = re.search(r'([A-Z][a-zA-Z0-9\s]{2,20}[0-9])', context)
                            if model_match:
                                model = model_match.group(1).strip()
                                if len(model) > 5:
                                    # 同時查找電郵
                                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', context)
                                    email = email_match.group(0) if email_match else ''
                                    
                                    leads.append({
                                        'phone': phone,
                                        'email': email,
                                        'model': model,
                                        'source': line[:80]
                                    })
                                    if email:
                                        print(f"    ✅ {model} - {phone} - {email}")
                                    else:
                                        print(f"    ✅ {model} - {phone}")
                    
                except Exception as e:
                    pass
            
        finally:
            browser.close()
    
    # 保存結果
    print(f"\n{'=' * 60}")
    print(f"📊 找到 {len(leads)} 條潛在線索")
    
    if leads:
        df = pd.DataFrame(leads)
        df = df.drop_duplicates(subset=['phone'])
        
        # 只保留 phone 列，取前30条
        df = df[['phone']].head(30)
        
        excel_path = DATA_DIR / f"28car_潛客_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(excel_path, index=False, header=['電話'])  # 保留中文表头
        print(f"📁 Excel 已保存: {excel_path}")
        print(f"   共 {len(df)} 条电话记录")
    
    print(f"{'=' * 60}")
    return leads

if __name__ == "__main__":
    scrape()
