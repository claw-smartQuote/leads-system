#!/usr/bin/env python3
"""
Facebook 快速測試腳本 - 只探索新帖子不提取留言
"""

import re
import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

CONFIG = {
    'GROUP_URLS': [
        'https://www.facebook.com/groups/hkdrivers/',
    ],
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
}

def random_delay(min_sec=2, max_sec=4):
    delay = random.uniform(min_sec, max_sec)
    print(f"    ⏱️ {delay:.1f}s")
    time.sleep(delay)

def main():
    print("="*60)
    print("🔍 Facebook 帖子探索測試")
    print("="*60)
    
    playwright = sync_playwright().start()
    
    # 啟動瀏覽器
    browser = playwright.chromium.launch(
        headless=True,
        slow_mo=50,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    
    # 載入登入狀態
    storage_state = None
    if CONFIG['STORAGE_STATE_PATH'].exists():
        storage_state = str(CONFIG['STORAGE_STATE_PATH'])
    
    context = browser.new_context(
        storage_state=storage_state,
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        locale='zh-HK',
    )
    
    # Stealth
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    
    page = context.new_page()
    page.set_default_timeout(30000)
    
    all_posts = []
    
    for group_url in CONFIG['GROUP_URLS']:
        print(f"\n🔍 探索: {group_url}")
        
        try:
            page.goto(group_url, wait_until='domcontentloaded', timeout=30000)
            random_delay(3, 5)
            
            # 滾動
            print("  📜 滾動...")
            for _ in range(4):
                page.evaluate('window.scrollBy(0, 800)')
                random_delay(2, 4)
            
            # 找 article 元素
            articles = page.locator('[role="article"]').all()
            print(f"  找到 {len(articles)} 個 article")
            
            seen = set()
            for article in articles:
                try:
                    links = article.locator('a[href*="facebook.com"]').all()
                    for link in links:
                        href = link.get_attribute('href', timeout=200) or ''
                        if '/groups/' in href and '/posts/' in href:
                            clean = re.sub(r'\?.*$', '', href.split('?')[0])
                            if clean and clean not in seen:
                                seen.add(clean)
                                all_posts.append(clean)
                except:
                    pass
                    
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
    
    print(f"\n{'='*60}")
    print(f"📋 發現 {len(all_posts)} 個帖子連結")
    print("="*60)
    
    for i, url in enumerate(all_posts[:5], 1):
        print(f"\n[{i}] {url}")
    
    print("\n✅ 測試完成")
    
    browser.close()
    playwright.stop()

if __name__ == '__main__':
    main()
