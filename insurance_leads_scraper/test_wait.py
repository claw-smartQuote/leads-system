#!/usr/bin/env python3
"""
測試 28car - 等待 iframe 載入
"""

from playwright.sync_api import sync_playwright
import time
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("🌐 訪問中...")
    page.goto("https://www.28car.com/sell_lst.php", wait_until='networkidle', timeout=60000)
    
    # 等待更長時間，讓 iframe 載入
    print("⏳ 等待 iframe 載入 (15秒)...")
    time.sleep(15)
    
    print(f"\n🖼️  總共 {len(page.frames)} 個 frames:")
    for i, frame in enumerate(page.frames):
        print(f"   Frame {i}: {frame.url[:80] if frame.url else '(no url)'}")
        try:
            html = frame.content()
            print(f"        HTML 長度: {len(html)}")
            if len(html) > 10000:
                # 檢查是否有車輛信息
                vids = re.findall(r'h_vid=(\d+)', html)
                if vids:
                    print(f"        ✅ 找到 {len(vids)} 個車輛 ID")
                    phones = re.findall(r'\d{4}[\s-]?\d{4}', html)
                    print(f"        📞 電話: {len(phones)} 個")
        except Exception as e:
            print(f"        ❌ 錯誤: {e}")
    
    print("\n✅ 完成")
    browser.close()
