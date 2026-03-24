#!/usr/bin/env python3
"""
Facebook 留言爬蟲 - 生產版 v2.0
功能：
- 提取指定貼文的所有留言
- 包含：留言者名稱、個人檔案連結、留言內容
- 自動滾動和展開所有留言
"""

import re
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# ==================== 設定 ====================
CONFIG = {
    # 目標貼文URL列表
    'POST_URLS': [
        'https://www.facebook.com/Zhuhaiinsurance/posts/pfbid0XSTnRUi6A6Xtq4P1tUka2mAt3Vfuiq3VeyvpqDSE1HzzbQ6ChLWJD5dPWiEQURjql',
    ],
    
    # 數據庫路徑
    'DB_PATH': Path.home() / '.fb_crawler' / 'fb_leads_v2.db',
    
    # Excel導出路徑
    'EXCEL_PATH': Path.home() / '.fb_crawler' / 'fb_潛客名單_v2.xlsx',
    
    # 登入狀態路徑
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
}

# ==================== 數據庫 ====================
def init_database():
    """初始化數據庫"""
    CONFIG['DB_PATH'].parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """保存潛客資料"""
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO fb_leads 
            (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['post_url'],
            data['commenter_name'],
            data['commenter_profile_url'],
            data['comment_text'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"  ⚠️ 保存失敗: {e}")
        return False

def export_to_excel(cursor):
    """導出到Excel"""
    cursor.execute('''
        SELECT commenter_name as 留言者名稱,
               commenter_profile_url as 個人檔案連結,
               comment_text as 留言內容,
               post_url as 貼文連結,
               scraped_at as 抓取時間
        FROM fb_leads
        ORDER BY scraped_at DESC
    ''')
    
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

# ==================== Facebook 爬蟲 ====================
class FacebookCommentCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        """啟動瀏覽器"""
        playwright = sync_playwright().start()
        
        self.browser = playwright.chromium.launch(
            headless=False,
            slow_mo=300,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 讀取登入狀態
        storage_state = None
        if CONFIG['STORAGE_STATE_PATH'].exists():
            print(f"🔑 使用登入狀態: {CONFIG['STORAGE_STATE_PATH']}")
            storage_state = str(CONFIG['STORAGE_STATE_PATH'])
        
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        self.page = self.context.new_page()
        
    def scroll_page(self, times=5):
        """滾動頁面加載內容"""
        for i in range(times):
            self.page.evaluate('window.scrollBy(0, 800)')
            import time
            time.sleep(1.5)
            
    def expand_comments(self):
        """展開所有留言"""
        import time
        max_attempts = 15
        
        for attempt in range(max_attempts):
            clicked = False
            
            # 找「查看更多留言」按鈕
            try:
                buttons = self.page.locator('[role="button"]').all()
                for btn in buttons:
                    try:
                        text = btn.inner_text(timeout=500)
                        if any(k in text for k in ['查看更多', '則留言', 'View more comments', 'comments']):
                            btn.click()
                            time.sleep(2)
                            clicked = True
                            break
                    except:
                        pass
            except:
                pass
            
            if not clicked:
                break
                
    def extract_comments(self, post_url):
        """提取留言資料"""
        import time
        comments = []
        
        print(f"\n🌐 訪問貼文: {post_url[:60]}...")
        self.page.goto(post_url, timeout=60000)
        time.sleep(5)
        
        # 滾動加載
        print("  滾動加載更多內容...")
        self.scroll_page(5)
        
        # 展開所有留言
        print("  展開所有留言...")
        self.expand_comments()
        
        # 再次滾動確保所有內容加載
        self.scroll_page(3)
        
        print("  提取留言資料...")
        
        # 策略: 使用多種選擇器組合
        # 方法1: 找所有用戶連結，然後找相鄰的留言內容
        
        all_elements = self.page.locator('div[role="article"], div[data-visualcompletion]').all()
        print(f"  找到 {len(all_elements)} 個可能包含留言的元素")
        
        # 方法2: 直接找所有用戶名稱連結
        profile_links = self.page.locator('a[href*="facebook.com"]').all()
        
        seen_profiles = set()
        
        for link in profile_links:
            try:
                href = link.get_attribute('href', timeout=100)
                if not href:
                    continue
                
                # 篩選用戶檔案連結
                is_user = (
                    '/profile.php' in href or
                    (re.match(r'https://www\.facebook\.com/[a-zA-Z0-9.]+/?$', href) and
                     not any(x in href for k in ['/posts/', '/groups/', '/pages/', '/events/', 
                                                  '/watch/', '/marketplace/', '/help/', '/privacy',
                                                  '/login', '/recover', '/l.php']))
                )
                
                if not is_user:
                    continue
                
                # 清理URL
                clean_url = href.split('?')[0].split('&')[0]
                
                # 去重
                if clean_url in seen_profiles:
                    continue
                seen_profiles.add(clean_url)
                
                # 獲取用戶名稱
                name = link.inner_text(timeout=200).strip()
                if not name or len(name) < 2:
                    continue
                
                # 排除非用戶名稱
                if name in ['讚', '回覆', 'Reply', 'Like', '更多', '分享', 'Comment', '登入']:
                    continue
                
                # 嘗試獲取留言內容
                comment_text = ""
                try:
                    # 策略: 從連結元素向上查找父容器，再找文字內容
                    parent = link.locator('xpath=ancestor::div[contains(@class, "x1y1aw1k") or contains(@class, "x1n2onr6") or @role="article"][1]')
                    
                    # 在父容器內找文字段落
                    text_elements = parent.locator('div[dir="auto"]').all()
                    for elem in text_elements:
                        text = elem.inner_text(timeout=300).strip()
                        # 排除用戶名稱和常見按鈕文字
                        if text and text != name and len(text) > 2:
                            if text not in ['讚', '回覆', 'Like', 'Reply', '更多']:
                                comment_text = text
                                break
                except:
                    pass
                
                # 如果上面失敗，嘗試備用策略
                if not comment_text:
                    try:
                        # 找同層級的下一個div
                        container = link.locator('xpath=..').locator('xpath=following-sibling::div[1]')
                        comment_text = container.inner_text(timeout=300).strip()
                    except:
                        pass
                
                comments.append({
                    'post_url': post_url,
                    'commenter_name': name,
                    'commenter_profile_url': clean_url,
                    'comment_text': comment_text[:500] if comment_text else "(無法提取)"
                })
                
            except Exception as e:
                continue
        
        return comments
    
    def close(self):
        """關閉瀏覽器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

# ==================== 主程序 ====================
def main():
    print("="*70)
    print("📘 Facebook 留言爬蟲 - 生產版 v2.0")
    print("="*70)
    
    # 初始化數據庫
    conn, cursor = init_database()
    
    # 啟動爬蟲
    crawler = FacebookCommentCrawler()
    crawler.start()
    
    total_saved = 0
    
    try:
        # 處理每個貼文
        for post_url in CONFIG['POST_URLS']:
            comments = crawler.extract_comments(post_url)
            
            # 保存到數據庫
            saved = 0
            for comment in comments:
                if save_lead(cursor, conn, comment):
                    saved += 1
            
            total_saved += saved
            print(f"  ✅ 保存 {saved}/{len(comments)} 條留言\n")
            
            import time
            time.sleep(3)
        
        # 導出Excel
        total_records = export_to_excel(cursor)
        
        print("="*70)
        print("✅ 爬蟲完成！")
        print("="*70)
        print(f"📊 本次新增: {total_saved} 條留言")
        print(f"📊 數據庫總計: {total_records} 條")
        print(f"📁 Excel導出: {CONFIG['EXCEL_PATH']}")
        
    finally:
        crawler.close()
        conn.close()

if __name__ == '__main__':
    main()
