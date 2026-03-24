#!/usr/bin/env python3
"""
快速測試 28car.com 數據提取
"""

from playwright.sync_api import sync_playwright
import time
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("🌐 訪問中...")
    page.goto("https://www.28car.com/sell_lst.php", wait_until='domcontentloaded', timeout=60000)
    time.sleep(10)
    
    # 找到正確的 frame
    print(f"🖼️  總共 {len(page.frames)} 個 frames:")
    target_frame = None
    for i, frame in enumerate(page.frames):
        url = frame.url
        print(f"   Frame {i}: {url[:80]}")
        if 'sell_lst' in url and '28car.com' in url:
            target_frame = frame
            print(f"   ✅ 使用 Frame {i}")
    
    if not target_frame:
        print("❌ 未找到 frame，使用第一個非主 frame")
        for frame in page.frames[1:]:
            if '28car.com' in frame.url:
                target_frame = frame
                break
    
    if not target_frame:
        print("❌ 仍未找到 frame")
        browser.close()
        exit()
    
    print("✅ Frame 找到")
    time.sleep(3)
    
    # 獲取頁面 HTML
    try:
        html = target_frame.content()
        print(f"📄 HTML 長度: {len(html)}")
        
        # 查找車輛鏈接
        vid_matches = re.findall(r'h_vid=(\d+)', html)
        print(f"🚗 找到 {len(vid_matches)} 個車輛 ID")
        
        # 查找電話
        phones = re.findall(r'\d{4}[\s-]?\d{4}', html)
        print(f"📞 找到 {len(phones)} 個電話號碼")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    
    # 查找車型（通過特定模式）
    # 從截圖看，車型格式如 "豐田 SPADE 1.5"
    car_patterns = [
        r'([\u4e00-\u9fa5]+\s+[A-Z0-9\s\.]+)',  # 中文 + 英文型號
    ]
    
    print("\n✅ 完成")
    browser.close()
