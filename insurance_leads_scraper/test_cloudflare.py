#!/usr/bin/env python3
"""
測試 28car.com - 使用 Playwright 繞過 Cloudflare
"""

from playwright.sync_api import sync_playwright
import time
import re

URL = "https://www.28car.com/sell_lst.php"

with sync_playwright() as p:
    # 使用更真實的瀏覽器配置來繞過檢測
    browser = p.chromium.launch(
        headless=False,  # 暫時用有頭模式看看
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='zh-HK',
        timezone_id='Asia/Hong_Kong',
    )
    
    # 繞過 webdriver 檢測
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    page = context.new_page()
    
    print("🌐 正在訪問 sell_lst.php...")
    page.goto(URL, wait_until='networkidle', timeout=60000)
    
    # 等待可能的 Cloudflare 驗證
    print("⏳ 等待頁面加載 (5秒)...")
    time.sleep(5)
    
    print(f"\n📄 當前 URL: {page.url}")
    print(f"📄 頁面標題: {page.title()}")
    
    # 檢查是否有 frame
    frames = page.frames
    print(f"\n🖼️  找到 {len(frames)} 個 frame")
    
    for i, frame in enumerate(frames):
        try:
            url = frame.url
            print(f"   Frame {i}: {url[:80]}")
        except:
            print(f"   Frame {i}: (無法獲取 URL)")
    
    # 嘗試獲取主內容
    html = page.content()
    print(f"\n📄 HTML 長度: {len(html)}")
    
    # 查找車輛信息
    if 'sell_detail' in html or 'selldetail' in html:
        print("✅ 找到車輛詳情鏈接!")
    
    # 嘗試找到表格
    tables = page.query_selector_all('table')
    print(f"📊 找到 {len(tables)} 個 table")
    
    rows = page.query_selector_all('tr')
    print(f"📊 找到 {len(rows)} 個 tr")
    
    # 如果有 frame，嘗試切換到第一個 frame 獲取內容
    if len(frames) > 1:
        print("\n🔄 嘗試從 frame 獲取內容...")
        for i, frame in enumerate(frames[1:], 1):  # 跳過主 frame
            try:
                frame_html = frame.content()
                if len(frame_html) > 5000:  # 有意義的內容
                    print(f"   Frame {i} 內容長度: {len(frame_html)}")
                    
                    # 保存 HTML 供分析
                    with open('/Users/claw/.openclaw/workspace/insurance_leads_scraper/frame_content.html', 'w', encoding='utf-8') as f:
                        f.write(frame_html[:50000])  # 保存前 50KB
                    print(f"   💾 已保存前 50KB 到 frame_content.html")
                    
                    # 查找車輛鏈接 - 多種模式
                    patterns = [
                        r'href=["\']([^"\']*sell_detail[^"\']*)["\']',
                        r'href=["\']([^"\']*selldetail[^"\']*)["\']',
                        r'href=["\']([^"\']*\/car\/[^"\']*)["\']',
                    ]
                    for pattern in patterns:
                        links = re.findall(pattern, frame_html, re.IGNORECASE)
                        if links:
                            print(f"   找到 {len(links)} 個車輛鏈接 (模式: {pattern[:40]})")
                            print(f"   示例: {links[0]}")
                            break
                    
                    # 查找表格結構
                    tables = frame.query_selector_all('table')
                    print(f"   Frame 內找到 {len(tables)} 個 table")
                    
                    rows = frame.query_selector_all('tr')
                    print(f"   Frame 內找到 {len(rows)} 個 tr")
                    
                    break
            except Exception as e:
                print(f"   Frame {i} 錯誤: {e}")
    
    print("\n✅ 測試完成")
    print("等待 3 秒後關閉...")
    time.sleep(3)
    browser.close()
