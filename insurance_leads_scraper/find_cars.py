#!/usr/bin/env python3
"""
找到真正的車輛數據行
"""

import time
import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
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
    
    rows = target_frame.query_selector_all('tr')
    print(f"總共 {len(rows)} 行\n")
    
    # 尋找包含 sell_dsp.php 的行
    car_rows = []
    for i, row in enumerate(rows):
        html = row.inner_html()
        if 'sell_dsp.php' in html or 'h_vid=' in html:
            car_rows.append((i, row))
    
    print(f"找到 {len(car_rows)} 行可能包含車輛數據\n")
    
    # 顯示前 10 個車輛行
    for idx, (row_num, row) in enumerate(car_rows[:10]):
        cells = row.query_selector_all('td')
        print(f"\n=== 車輛行 {row_num}: {len(cells)} 個單元格 ===")
        
        for j, cell in enumerate(cells):
            text = cell.inner_text().strip()[:60]
            link = cell.query_selector('a')
            href = link.get_attribute('href') if link else None
            
            if href and ('sell_dsp' in href or 'h_vid=' in href):
                print(f"  列{j}: 【車型】{text}")
                print(f"       鏈接: {href[:60]}")
            elif text and j < 6:
                # 查找電話
                phone_match = re.search(r'\d{4}[\s-]?\d{4}', text)
                if phone_match:
                    print(f"  列{j}: 【電話】{phone_match.group()}")
                elif len(text) > 5 and j < 4:
                    print(f"  列{j}: {text[:50]}")
    
    browser.close()
