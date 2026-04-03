#!/usr/bin/env python3
"""
測試 28car.com - 使用 JavaScript 獲取內容
"""

from playwright.sync_api import sync_playwright
import time
import re

URL = "https://www.28car.com/sell_lst.php"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='zh-HK',
    )
    
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    
    page = context.new_page()
    
    print("🌐 訪問 28car.com...")
    page.goto(URL, wait_until='domcontentloaded', timeout=60000)
    
    # 等待更長時間
    print("⏳ 等待頁面載入 (10秒)...")
    time.sleep(10)
    
    # 使用 evaluate 獲取頁面內容
    html_content = page.evaluate("""() => {
        // 嘗試獲取所有 frame 的內容
        let content = '';
        for (let i = 0; i < frames.length; i++) {
            try {
                const frame = frames[i];
                if (frame.document && frame.document.body) {
                    content += '___FRAME_' + i + '___' + frame.document.body.innerHTML.substring(0, 100000);
                }
            } catch(e) {}
        }
        return content;
    }""")
    
    print(f"📄 獲取到的內容長度: {len(html_content)}")
    
    # 檢查是否有車輛信息
    if 'sell_dsp' in html_content or 'h_vid' in html_content:
        print("✅ 找到車輛相關內容!")
        
        # 提取車輛信息
        vid_matches = re.findall(r'h_vid[="]*(\d+)', html_content)
        print(f"🚗 找到 {len(vid_matches)} 個車輛 ID")
        
        # 嘗試提取車型
        model_patterns = [
            r'<a[^>]*href[^>]*sell_dsp[^>]*>([^<]{3,50})</a>',
            r'title="([^"]*[^0-9][^"]{3,30})"',  # 車型通常在 title 屬性
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"📝 找到候選車型: {matches[:5]}")
                break
    else:
        print("⚠️ 未找到車輛信息，檢查頁面內容...")
        print(f"📄 內容前 2000 字符: {html_content[:2000]}")
    
    # 截圖看看
    print("\n📸 截圖保存...")
    page.screenshot(path='/Users/claw/.openclaw/workspace/insurance_leads_scraper/screenshot.png')
    
    print("✅ 完成")
    time.sleep(2)
    browser.close()
