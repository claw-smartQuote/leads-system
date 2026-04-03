#!/usr/bin/env python3
"""
分析 28car.com 表格結構
"""

import time
import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("🌐 訪問頁面...")
    page.goto("https://www.28car.com/sell_lst.php", wait_until='networkidle', timeout=60000)
    time.sleep(8)
    
    # 找到內容 frame
    target_frame = None
    for frame in page.frames:
        if 'sell_lst' in frame.url and '28car.com' in frame.url:
            try:
                html = frame.content()
                if len(html) > 100000:
                    target_frame = frame
                    break
            except:
                pass
    
    if not target_frame:
        print("❌ 未找到 frame")
        browser.close()
        exit()
    
    # 獲取行
    rows = target_frame.query_selector_all('tr')
    print(f"找到 {len(rows)} 行\n")
    
    # 分析前 30 行
    for i, row in enumerate(rows[:30]):
        cells = row.query_selector_all('td')
        if len(cells) < 2:
            continue
        
        print(f"\n=== 行 {i}: {len(cells)} 個單元格 ===")
        
        for j, cell in enumerate(cells[:6]):  # 只看前6列
            text = cell.inner_text().strip()[:50]  # 只顯示前50字符
            link = cell.query_selector('a')
            href = link.get_attribute('href')[:40] if link else '無鏈接'
            print(f"  列{j}: {text} | {href}")
    
    browser.close()
