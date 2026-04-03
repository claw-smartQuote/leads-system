#!/usr/bin/env python3
"""
Facebook 智能搜尋+爬蟲 - 綜合版 v6.0
功能：自動搜尋關鍵字 → 提取貼文連結 → 爬取留言
"""

import re
import time
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# ==================== 設定 ====================
CONFIG = {
    # 搜尋關鍵字
    'SEARCH_KEYWORDS': ['港車北上', '汽車保險', '車輛買賣'],
    
    # 每個關鍵字最多處理的貼文數
    'MAX_POSTS_PER_KEYWORD': 5,
    
    # 數據庫路徑
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_search.db'),
    'EXCEL_PATH': Path('/Users/claw/.openclaw/workspace/fb_潛客_搜尋結果.xlsx'),
    
    # 登入狀態
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
}

# ==================== 數據庫 ====================
def init_database():
    CONFIG['DB_PATH'].parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_keyword TEXT,
            post_url TEXT,
            commenter_name TEXT,
            commenter_profile_url TEXT,
            comment_text TEXT,
            scraped_at TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def save_lead(cursor, conn, data):
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO fb_leads 
            (search_keyword, post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data.get('search_keyword', ''),
            data['post_url'], data['commenter_name'], data['commenter_profile_url'],
            data['comment_text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"  ⚠️ 保存失敗: {e}")
        return False

def export_to_excel(cursor):
    cursor.execute('''
        SELECT search_keyword, commenter_name, commenter_profile_url, comment_text, post_url, scraped_at 
        FROM fb_leads ORDER BY scraped_at DESC
    ''')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['搜尋關鍵字', '留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

# ==================== Facebook 綜合爬蟲 ====================
class FacebookSearchCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        """啟動瀏覽器"""
        playwright = sync_playwright().start()
        
        self.browser = playwright.chromium.launch(
            headless=False,
            slow_mo=800,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        storage_state = str(CONFIG['STORAGE_STATE_PATH']) if CONFIG['STORAGE_STATE_PATH'].exists() else None
        if storage_state:
            print(f"🔑 加載登入狀態")
        
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            locale='zh-HK',
        )
        
        self.context.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        ''')
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)
        
    def search_posts(self, keyword):
        """
        搜尋貼文並提取連結
        策略：直接訪問搜尋URL，然後提取頁面中所有貼文連結
        """
        print(f"\n🔍 搜尋關鍵字: '{keyword}'")
        
        # 構建搜尋URL
        search_url = f'https://www.facebook.com/search/posts?q={keyword}'
        print(f"  訪問: {search_url}")
        
        try:
            self.page.goto(search_url, wait_until='networkidle', timeout=90000)
            time.sleep(5)
            
            # 滾動加載更多結果
            print("  滾動加載結果...")
            for _ in range(5):
                self.page.evaluate('window.scrollBy(0, 1000)')
                time.sleep(2)
            
            # 提取貼文連結 - 多種策略
            post_urls = []
            
            # 策略1: 找所有連結，篩選包含 /posts/ 的
            all_links = self.page.locator('a').all()
            print(f"  頁面共有 {len(all_links)} 個連結")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href', timeout=100) or ''
                    
                    # 篩選貼文連結
                    if '/posts/' in href and 'facebook.com' in href:
                        # 清理URL
                        clean_url = href.split('?')[0].split('&')[0]
                        
                        # 排除重複
                        if clean_url not in post_urls:
                            post_urls.append(clean_url)
                            
                    if len(post_urls) >= CONFIG['MAX_POSTS_PER_KEYWORD']:
                        break
                        
                except:
                    pass
            
            print(f"  ✅ 找到 {len(post_urls)} 個貼文")
            return post_urls
            
        except Exception as e:
            print(f"  ❌ 搜尋失敗: {e}")
            return []
    
    def extract_comments_from_post(self, post_url, keyword):
        """從單個貼文提取留言（使用v5.0的邏輯）"""
        print(f"\n  📄 處理貼文: {post_url[:50]}...")
        
        try:
            self.page.goto(post_url, wait_until='networkidle', timeout=90000)
            time.sleep(5)
            
            # 滾動加載
            for _ in range(5):
                self.page.evaluate('window.scrollBy(0, 800)')
                time.sleep(1.5)
            
            # 展開留言
            for _ in range(10):
                try:
                    buttons = self.page.locator('[role="button"]').all()
                    clicked = False
                    for btn in buttons:
                        text = btn.inner_text(timeout=500).lower()
                        if any(k in text for k in ['更多', 'more', '則']):
                            btn.click()
                            time.sleep(2)
                            clicked = True
                            break
                    if not clicked:
                        break
                except:
                    break
            
            # 再次滾動
            for _ in range(3):
                self.page.evaluate('window.scrollBy(0, 800)')
                time.sleep(1.5)
            
            # 提取留言
            comments = []
            seen = set()
            
            # 使用 role="article" 策略
            articles = self.page.locator('[role="article"]').all()
            
            for article in articles:
                try:
                    # 找用戶連結
                    user_link = article.locator('a[href*="facebook.com"]').first
                    if user_link.count() == 0:
                        continue
                    
                    href = user_link.get_attribute('href', timeout=500) or ''
                    name = user_link.inner_text(timeout=500).strip()
                    
                    # 篩選
                    if not name or len(name) < 2 or len(name) > 40:
                        continue
                    if name in ['讚', '回覆', 'Like', 'Reply', '更多']:
                        continue
                    
                    # 清理URL
                    clean_url = None
                    if '/profile.php?id=' in href:
                        match = re.search(r'id=(\d+)', href)
                        if match:
                            clean_url = f"https://www.facebook.com/profile.php?id={match.group(1)}"
                    elif 'facebook.com/' in href:
                        match = re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)', href)
                        if match:
                            username = match.group(1)
                            if username not in ['login', 'recover', 'help', 'watch']:
                                clean_url = f"https://www.facebook.com/{username}"
                    
                    if not clean_url or clean_url in seen:
                        continue
                    seen.add(clean_url)
                    
                    # 提取留言內容
                    comment_text = ""
                    try:
                        text_divs = article.locator('div[dir="auto"]').all()
                        for div in text_divs:
                            text = div.inner_text(timeout=300).strip()
                            if text and text != name and len(text) > 2:
                                if text not in ['讚', '回覆', 'Like', 'Reply']:
                                    comment_text = text
                                    break
                    except:
                        pass
                    
                    comments.append({
                        'search_keyword': keyword,
                        'post_url': post_url,
                        'commenter_name': name,
                        'commenter_profile_url': clean_url,
                        'comment_text': comment_text[:500] if comment_text else "(無法提取)"
                    })
                    
                except:
                    pass
            
            return comments
            
        except Exception as e:
            print(f"    ❌ 提取失敗: {e}")
            return []
    
    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

# ==================== 主程序 ====================
def main():
    print("="*70)
    print("📘 Facebook 智能搜尋+爬蟲 v6.0")
    print("="*70)
    print(f"搜尋關鍵字: {', '.join(CONFIG['SEARCH_KEYWORDS'])}")
    print(f"每關鍵字最多: {CONFIG['MAX_POSTS_PER_KEYWORD']} 個貼文\n")
    
    conn, cursor = init_database()
    crawler = FacebookSearchCrawler()
    
    try:
        crawler.start()
        
        total_comments = 0
        
        # 處理每個關鍵字
        for idx, keyword in enumerate(CONFIG['SEARCH_KEYWORDS'], 1):
            print(f"\n{'='*70}")
            print(f"[{idx}/{len(CONFIG['SEARCH_KEYWORDS'])}] 關鍵字: {keyword}")
            print('='*70)
            
            # 搜尋貼文
            post_urls = crawler.search_posts(keyword)
            
            if not post_urls:
                print(f"  ⚠️ 未找到貼文，跳過")
                continue
            
            # 處理每個貼文
            for post_idx, post_url in enumerate(post_urls, 1):
                print(f"\n  [{post_idx}/{len(post_urls)}] 處理貼文...")
                
                comments = crawler.extract_comments_from_post(post_url, keyword)
                
                # 保存
                saved = 0
                for comment in comments:
                    if save_lead(cursor, conn, comment):
                        saved += 1
                        print(f"      ✅ {comment['commenter_name']}: {comment['comment_text'][:25]}...")
                
                total_comments += saved
                print(f"    📊 保存 {saved}/{len(comments)} 條")
                
                # 休息避免限制
                time.sleep(3)
            
            # 關鍵字之間休息
            if idx < len(CONFIG['SEARCH_KEYWORDS']):
                print(f"\n  ⏱️  休息5秒...")
                time.sleep(5)
        
        # 導出Excel
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 全部完成！")
        print("="*70)
        print(f"📊 本次新增: {total_comments} 條留言")
        print(f"📊 數據庫總計: {total_records} 條")
        print(f"📁 Excel: {CONFIG['EXCEL_PATH']}")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        crawler.close()
        conn.close()
        print("\n👋 瀏覽器已關閉")

if __name__ == '__main__':
    main()
