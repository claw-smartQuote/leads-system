#!/usr/bin/env python3
"""
Facebook 爬蟲 - 調試版
用於測試和調整選擇器，可逐步調試每個步驟
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# 設定
STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'

def ensure_login():
    """確保有登入狀態"""
    if not STORAGE_STATE_PATH.exists():
        print("🔐 首次使用，需要登入Facebook")
        print("="*60)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=300)
            context = browser.new_context(viewport={'width': 1400, 'height': 900})
            page = context.new_page()
            
            # 前往Facebook
            page.goto('https://www.facebook.com/', timeout=60000)
            print("請在瀏覽器中登入Facebook...")
            input("登入完成後按 Enter 繼續...")
            
            # 儲存登入狀態
            STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(STORAGE_STATE_PATH))
            print(f"✅ 登入狀態已儲存: {STORAGE_STATE_PATH}")
            
            browser.close()
    else:
        print(f"✅ 使用已儲存的登入狀態")

def test_search():
    """測試搜尋功能"""
    print("\n" + "="*60)
    print("🔍 測試搜尋功能")
    print("="*60)
    
    keyword = input("輸入搜尋關鍵字（預設: 汽車保險）: ").strip() or "汽車保險"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        
        # 讀取登入狀態
        storage_state = str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH.exists() else None
        context = browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900}
        )
        page = context.new_page()
        
        # 搜尋
        search_url = f'https://www.facebook.com/search/posts?q={keyword}'
        print(f"訪問: {search_url}")
        page.goto(search_url, timeout=60000)
        
        input("\n檢查搜尋結果頁面，按 Enter 繼續...")
        
        # 嘗試提取貼文連結
        print("\n嘗試提取貼文連結...")
        
        # 方法1: ARIA標籤
        links = page.locator('a[role="link"]').all()
        print(f"找到 {len(links)} 個 role=link 的連結")
        
        post_urls = []
        for link in links[:20]:
            try:
                href = link.get_attribute('href')
                text = link.inner_text(timeout=500)
                if href and ('/posts/' in href or '/groups/' in href):
                    clean_url = href.split('?')[0]
                    if clean_url not in post_urls:
                        post_urls.append(clean_url)
                        print(f"  📄 {text[:30] if text else 'No text'}...")
                        print(f"     URL: {clean_url[:80]}...")
            except:
                pass
        
        print(f"\n共找到 {len(post_urls)} 個貼文連結")
        
        browser.close()
        return post_urls

def test_post_extraction(post_url=None):
    """測試單個貼文的留言提取"""
    print("\n" + "="*60)
    print("📝 測試留言提取")
    print("="*60)
    
    if not post_url:
        post_url = input("輸入貼文URL: ").strip()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        
        storage_state = str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH.exists() else None
        context = browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900}
        )
        page = context.new_page()
        
        print(f"訪問貼文: {post_url}")
        page.goto(post_url, timeout=60000)
        time.sleep(3)
        
        input("\n檢查貼文頁面，按 Enter 繼續...")
        
        # 測試展開留言
        print("\n嘗試展開更多留言...")
        
        for attempt in range(5):
            # 找「查看更多」按鈕
            buttons = page.locator('[role="button"]').all()
            clicked = False
            
            for btn in buttons:
                try:
                    text = btn.inner_text(timeout=500)
                    if any(kw in text for kw in ['查看更多', '則留言', 'comments', 'View']):
                        print(f"  點擊: {text[:50]}")
                        btn.click()
                        time.sleep(2)
                        clicked = True
                        break
                except:
                    pass
            
            if not clicked:
                print("  沒有更多按鈕可點擊")
                break
        
        # 測試提取留言者
        print("\n嘗試提取留言者資料...")
        
        # 方法: 找所有用戶名稱連結
        # Facebook的用戶連結通常有特定模式
        
        results = []
        
        # 策略1: 找所有a標籤，篩選出用戶檔案連結
        all_links = page.locator('a').all()
        print(f"頁面共有 {len(all_links)} 個連結")
        
        for link in all_links:
            try:
                href = link.get_attribute('href', timeout=100)
                if not href:
                    continue
                
                # 篩選用戶檔案連結
                is_profile = (
                    '/profile.php' in href or
                    (href.startswith('https://www.facebook.com/') and 
                     not any(x in href for x in ['/posts/', '/groups/', '/pages/', '/events/', '/watch/', '/marketplace/', '/help/', '/privacy/', '/terms/', '/careers/', '/about/']))
                )
                
                if is_profile:
                    text = link.inner_text(timeout=500).strip()
                    # 排除非用戶名稱
                    if text and len(text) > 1 and text not in ['讚', '回覆', 'Reply', 'Like', '更多']:
                        if not text.startswith('http'):
                            results.append({'name': text, 'url': href.split('?')[0]})
                            print(f"  👤 {text}")
                            print(f"     {href.split('?')[0][:80]}...")
            except:
                pass
        
        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique_results.append(r)
        
        print(f"\n共找到 {len(unique_results)} 個唯一留言者")
        
        # 測試提取留言內容
        print("\n嘗試提取留言內容...")
        # 這部分需要根據實際HTML結構調整
        
        input("\n檢查結果，按 Enter 結束...")
        browser.close()

def show_html_structure():
    """顯示當前頁面的HTML結構，用於分析"""
    print("\n" + "="*60)
    print("🔬 分析HTML結構")
    print("="*60)
    
    url = input("輸入要分析的URL: ").strip()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH.exists() else None,
            viewport={'width': 1400, 'height': 900}
        )
        page = context.new_page()
        
        page.goto(url, timeout=60000)
        time.sleep(3)
        
        print("\n頁面已加載，請用瀏覽器的開發者工具檢查元素")
        print("在終端中你可以執行以下Playwright命令:")
        print("  - page.content() 獲取完整HTML")
        print("  - page.locator('...').all() 測試選擇器")
        
        input("\n分析完成後按 Enter 結束...")
        browser.close()

def main():
    """主選單"""
    print("="*70)
    print("📘 Facebook 爬蟲 - 調試工具")
    print("="*70)
    
    # 確保登入
    ensure_login()
    
    while True:
        print("\n" + "="*60)
        print("請選擇功能:")
        print("="*60)
        print("1. 測試搜尋功能")
        print("2. 測試貼文留言提取")
        print("3. 分析HTML結構")
        print("4. 退出")
        
        choice = input("\n選擇 (1-4): ").strip()
        
        if choice == '1':
            test_search()
        elif choice == '2':
            test_post_extraction()
        elif choice == '3':
            show_html_structure()
        elif choice == '4':
            print("\n再見！")
            break
        else:
            print("無效選擇")

if __name__ == '__main__':
    main()
