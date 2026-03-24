#!/usr/bin/env python3
"""
測試 28car.com - 直接從 Frame 獲取車輛列表
"""

from playwright.sync_api import sync_playwright
import time
import re

URL = "https://www.28car.com/sell_lst.php"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # 使用有頭模式確保內容加載
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='zh-HK',
        timezone_id='Asia/Hong_Kong',
    )
    
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    page = context.new_page()
    
    print("🌐 正在訪問 sell_lst.php...")
    page.goto(URL, wait_until='networkidle', timeout=60000)
    
    # 等待頁面加載
    print("⏳ 等待 5 秒...")
    time.sleep(5)
    
    # 找到包含內容的 frame
    frames = page.frames
    print(f"🖼️  找到 {len(frames)} 個 frame")
    
    target_frame = None
    for frame in frames:
        if '28car.com' in frame.url and 'sell_lst' in frame.url:
            target_frame = frame
            print(f"✅ 使用 Frame: {frame.url}")
            break
    
    if not target_frame:
        print("❌ 未找到目標 frame")
        browser.close()
        exit()
    
    # 等待表格加載
    print("⏳ 等待表格加載...")
    try:
        target_frame.wait_for_selector('table', timeout=10000)
    except:
        print("⚠️ 等待超時，繼續嘗試...")
    
    time.sleep(3)
    
    # 獲取所有行
    rows = target_frame.query_selector_all('tr')
    print(f"📊 找到 {len(rows)} 個表格行")
    
    cars = []
    for i, row in enumerate(rows):
        try:
            # 嘗試找到車輛信息
            cells = row.query_selector_all('td')
            if len(cells) >= 4:
                # 第二個單元格通常是車型
                model_cell = cells[1]
                model_link = model_cell.query_selector('a')
                
                if model_link:
                    car_model = model_link.inner_text().strip()
                    detail_url = model_link.get_attribute('href')
                    
                    # 第四個單元格通常是價格
                    price_cell = cells[3]
                    price_text = price_cell.inner_text().strip()
                    
                    # 提取車輛 ID
                    vid_match = re.search(r'h_vid=(\d+)', detail_url) if detail_url else None
                    vid = vid_match.group(1) if vid_match else ''
                    
                    if car_model and len(car_model) > 3:
                        cars.append({
                            'model': car_model,
                            'price': price_text,
                            'url': detail_url,
                            'vid': vid
                        })
                        print(f"  [{len(cars)}] {car_model} - {price_text}")
                        
                        if len(cars) >= 10:  # 只顯示前 10 個
                            break
        except Exception as e:
            continue
    
    print(f"\n✅ 總共找到 {len(cars)} 輛車")
    
    # 測試進入詳情頁
    if cars:
        print(f"\n🧪 測試進入詳情頁: {cars[0]['url']}")
        target_frame.goto(cars[0]['url'], wait_until='domcontentloaded')
        time.sleep(3)
        
        page_text = target_frame.inner_text('body')
        
        # 查找電話
        phones = re.findall(r'\d{4}[\s-]?\d{4}', page_text)
        print(f"📞 找到電話: {phones[:3]}")
        
        # 查找聯絡人
        name_match = re.search(r'聯絡[人:]?\s*([^\n]{2,20})', page_text)
        if name_match:
            print(f"👤 聯絡人: {name_match.group(1).strip()}")
    
    print("\n✅ 測試完成")
    time.sleep(2)
    browser.close()
