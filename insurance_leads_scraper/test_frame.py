#!/usr/bin/env python3
"""
測試 28car.com - 從正確的 Frame 獲取車輛數據
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
    page.goto(URL, wait_until='networkidle', timeout=60000)
    
    print("⏳ 等待內容載入 (8秒)...")
    time.sleep(8)
    
    # 找到包含實際內容的 frame（不是主 frame）
    target_frame = None
    for frame in page.frames:
        frame_url = frame.url
        print(f"  Frame: {frame_url[:60]}")
        
        # 找到包含 sell_lst 的 frame，但不是主域名
        if 'sell_lst' in frame_url and 'dj' in frame_url:
            target_frame = frame
            print(f"  ✅ 目標 Frame 找到: {frame_url}")
            break
    
    if not target_frame:
        print("❌ 未找到目標 frame")
        browser.close()
        exit()
    
    # 等待表格出現
    print("⏳ 等待表格...")
    target_frame.wait_for_selector('table', timeout=15000)
    time.sleep(2)
    
    # 獲取所有行
    rows = target_frame.query_selector_all('tr')
    print(f"\n📊 找到 {len(rows)} 行")
    
    cars = []
    for i, row in enumerate(rows):
        try:
            cells = row.query_selector_all('td')
            if len(cells) < 4:
                continue
            
            # 獲取車型
            model_cell = cells[1]
            model_link = model_cell.query_selector('a')
            car_model = model_link.inner_text().strip() if model_link else model_cell.inner_text().strip()
            
            # 獲取詳情鏈接
            detail_url = model_link.get_attribute('href') if model_link else ''
            
            # 獲取價格
            price_cell = cells[4] if len(cells) > 4 else cells[3]
            price_text = price_cell.inner_text().strip()
            
            # 獲取備註/描述（可能包含電話）
            desc_cell = cells[2] if len(cells) > 2 else None
            desc_text = desc_cell.inner_text().strip() if desc_cell else ''
            
            # 檢查是否有電話
            phone_match = re.search(r'(?:電話|Tel|Tel[.:]|聯絡).*?(\d{4}[\s-]?\d{4})', desc_text + ' ' + price_text)
            phone = phone_match.group(1) if phone_match else ''
            
            # 過濾有效車輛
            if car_model and len(car_model) > 2 and not car_model.startswith('$'):
                vid = ''
                if detail_url:
                    vid_match = re.search(r'h_vid=(\d+)', detail_url)
                    vid = vid_match.group(1) if vid_match else ''
                
                cars.append({
                    'model': car_model,
                    'price': price_text,
                    'phone': phone,
                    'desc': desc_text[:100],
                    'vid': vid
                })
                
                if len(cars) <= 10:  # 只顯示前 10 個
                    print(f"  [{len(cars)}] {car_model}")
                    print(f"      價格: {price_text}")
                    print(f"      電話: {phone if phone else '未找到'}")
        
        except Exception as e:
            continue
    
    print(f"\n✅ 總共找到 {len(cars)} 輛車")
    
    # 統計有電話的車輛
    with_phone = [c for c in cars if c['phone']]
    print(f"📞 其中 {len(with_phone)} 輛有電話號碼")
    
    print("\n✅ 測試完成")
    time.sleep(3)
    browser.close()
