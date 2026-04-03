#!/usr/bin/env python3
"""
Facebook 留言爬蟲 - 完整版
功能：
- 搜尋「汽車保險」「港車北上」相關貼文
- 展開所有留言（自動點擊「查看更多」）
- 提取留言者名稱、個人檔案連結、留言內容
- 使用結構化選擇器（不依賴動態class name）
- 支持登入狀態（Cookie/Storage State）

作者: OpenClaw
版本: v1.0
"""

import json
import time
import re
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ==================== 設定 ====================
CONFIG = {
    # 搜尋關鍵字（會逐個搜尋）
    'SEARCH_KEYWORDS': ['汽車保險', '港車北上'],
    
    # 每個關鍵字最多處理的貼文數量
    'MAX_POSTS_PER_KEYWORD': 10,
    
    # 每個貼文最多提取的留言數量
    'MAX_COMMENTS_PER_POST': 100,
    
    # 瀏覽器設定
    'HEADLESS': False,  # 設為True可在背景運行
    'SLOW_MO': 500,  # 操作延遲（毫秒），避免被偵測
    
    # 登入狀態儲存路徑
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
    
    # 數據庫路徑
    'DB_PATH': Path.home() / '.fb_crawler' / 'fb_leads.db',
    
    # Excel導出路徑
    'EXCEL_PATH': Path.home() / '.fb_crawler' / 'fb_潛客名單.xlsx',
}

# ==================== 數據庫初始化 ====================
def init_database():
    """初始化SQLite數據庫"""
    CONFIG['DB_PATH'].parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_keyword TEXT,
            post_url TEXT,
            post_title TEXT,
            commenter_name TEXT,
            commenter_profile_url TEXT,
            comment_text TEXT,
            comment_time TEXT,
            scraped_at TEXT
        )
    ''')
    
    conn.commit()
    return conn, cursor

def save_comment(cursor, conn, data):
    """保存單條留言到數據庫"""
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO fb_comments 
            (search_keyword, post_url, post_title, commenter_name, commenter_profile_url, comment_text, comment_time, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['search_keyword'],
            data['post_url'],
            data['post_title'],
            data['commenter_name'],
            data['commenter_profile_url'],
            data['comment_text'],
            data.get('comment_time', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"  ⚠️ 保存失敗: {e}")
        return False

def export_to_excel(cursor):
    """導出數據到Excel"""
    cursor.execute('''
        SELECT search_keyword as 搜尋關鍵字,
               commenter_name as 留言者名稱,
               commenter_profile_url as 個人檔案連結,
               comment_text as 留言內容,
               post_title as 貼文標題,
               post_url as 貼文連結,
               comment_time as 留言時間,
               scraped_at as 抓取時間
        FROM fb_comments
        ORDER BY scraped_at DESC, search_keyword
    ''')
    
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=[
        '搜尋關鍵字', '留言者名稱', '個人檔案連結', '留言內容',
        '貼文標題', '貼文連結', '留言時間', '抓取時間'
    ])
    
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

# ==================== Facebook 爬蟲核心 ====================
class FacebookCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        """啟動瀏覽器"""
        playwright = sync_playwright().start()
        
        # 啟動瀏覽器
        self.browser = playwright.chromium.launch(
            headless=CONFIG['HEADLESS'],
            slow_mo=CONFIG['SLOW_MO'],
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 讀取儲存的登入狀態（如果有）
        storage_state = None
        if CONFIG['STORAGE_STATE_PATH'].exists():
            print(f"🔑 讀取登入狀態: {CONFIG['STORAGE_STATE_PATH']}")
            storage_state = str(CONFIG['STORAGE_STATE_PATH'])
        
        # 創建瀏覽器上下文
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 注入腳本隱藏自動化痕跡
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = self.context.new_page()
        
    def check_login_status(self):
        """檢查是否已登入"""
        self.page.goto('https://www.facebook.com/', timeout=60000)
        time.sleep(3)
        
        # 檢查是否有登入表單
        login_form = self.page.locator('input[name="email"]').count() > 0
        
        if login_form:
            print("⚠️ 未登入狀態，請手動登入...")
            return False
        else:
            print("✅ 已登入狀態")
            return True
    
    def manual_login(self):
        """手動登入流程"""
        print("\n" + "="*60)
        print("🔐 Facebook 登入")
        print("="*60)
        print("請在瀏覽器中手動登入Facebook")
        print("登入成功後，輸入 'y' 繼續...")
        
        # 等待用戶確認
        user_input = input("已登入？(y/n): ").strip().lower()
        
        if user_input == 'y':
            # 儲存登入狀態
            CONFIG['STORAGE_STATE_PATH'].parent.mkdir(parents=True, exist_ok=True)
            self.context.storage_state(path=str(CONFIG['STORAGE_STATE_PATH']))
            print(f"✅ 登入狀態已儲存: {CONFIG['STORAGE_STATE_PATH']}")
            return True
        else:
            return False
    
    def search_posts(self, keyword):
        """搜尋貼文"""
        print(f"\n🔍 搜尋關鍵字: '{keyword}'")
        
        # 構建搜尋URL
        search_url = f'https://www.facebook.com/search/posts?q={keyword}'
        self.page.goto(search_url, timeout=60000)
        time.sleep(5)
        
        posts = []
        
        # 提取貼文連結（使用多種選擇器策略）
        # 策略1: 使用ARIA標籤
        post_links = self.page.locator('a[href*="/posts/"], a[href*="/groups/"]').all()
        
        for link in post_links[:CONFIG['MAX_POSTS_PER_KEYWORD']]:
            try:
                href = link.get_attribute('href')
                if href and '/posts/' in href:
                    # 清理URL，移除追蹤參數
                    clean_url = href.split('?')[0]
                    if clean_url not in [p['url'] for p in posts]:
                        posts.append({'url': clean_url, 'title': ''})
            except:
                continue
        
        print(f"  找到 {len(posts)} 個貼文")
        return posts
    
    def expand_comments(self):
        """展開所有留言"""
        max_attempts = 20
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            clicked = False
            
            # 策略1: 使用ARIA標籤找「查看更多留言」按鈕
            try:
                buttons = self.page.locator('[role="button"]').all()
                for btn in buttons:
                    text = btn.inner_text(timeout=1000)
                    if any(keyword in text for keyword in ['查看更多留言', 'View more comments', '則留言', 'comments']):
                        btn.click()
                        time.sleep(2)
                        clicked = True
                        print(f"    點擊展開更多留言...")
                        break
            except:
                pass
            
            # 策略2: 使用XPath找特定文字
            if not clicked:
                try:
                    more_buttons = self.page.locator('text=/查看更多|View more|則留言/i').all()
                    for btn in more_buttons[:1]:
                        btn.click()
                        time.sleep(2)
                        clicked = True
                        break
                except:
                    pass
            
            if not clicked:
                break
        
        print(f"    留言展開完成（嘗試{attempts}次）")
    
    def scroll_to_load(self, scroll_times=5):
        """滾動頁面加載更多內容"""
        for i in range(scroll_times):
            self.page.evaluate('window.scrollBy(0, 800)')
            time.sleep(1.5)
    
    def extract_comments(self, post_url, keyword):
        """提取留言數據"""
        comments = []
        
        try:
            # 訪問貼文
            self.page.goto(post_url, timeout=60000)
            time.sleep(5)
            
            # 展開所有留言
            self.expand_comments()
            
            # 滾動確保所有內容加載
            self.scroll_to_load(3)
            
            # 提取貼文標題（前100字）
            post_title = ""
            try:
                # 策略: 找包含文字內容的div
                content_divs = self.page.locator('div[dir="auto"]').all()
                for div in content_divs[:3]:
                    text = div.inner_text(timeout=1000)
                    if len(text) > 10:
                        post_title = text[:100]
                        break
            except:
                pass
            
            # 提取留言 - 使用結構化選擇器（不依賴動態class）
            # 策略: 使用ARIA role和結構層級
            
            # 方法1: 找所有用戶名稱連結
            profile_links = self.page.locator('a[href*="/profile.php"], a[href^="https://www.facebook.com/"][role="link"]').all()
            
            processed_profiles = set()
            
            for link in profile_links[:CONFIG['MAX_COMMENTS_PER_POST']]:
                try:
                    # 獲取個人檔案URL
                    href = link.get_attribute('href')
                    if not href:
                        continue
                    
                    # 清理URL
                    if '/profile.php' in href:
                        profile_url = href.split('&')[0]
                    else:
                        profile_url = href.split('?')[0]
                    
                    # 去重
                    if profile_url in processed_profiles:
                        continue
                    processed_profiles.add(profile_url)
                    
                    # 獲取用戶名稱
                    name = link.inner_text(timeout=1000).strip()
                    if not name or len(name) < 2:
                        continue
                    
                    # 排除「讚」、「回覆」等非用戶名稱
                    if name in ['讚', '回覆', 'Reply', 'Like', '愛心', '哈', '哇', '嗚', '更多']:
                        continue
                    
                    # 獲取留言內容
                    comment_text = ""
                    try:
                        # 策略: 從用戶名稱向上查找父元素，再找留言內容
                        parent = link.locator('xpath=../..')
                        
                        # 在同層級找文字內容
                        text_divs = parent.locator('div[dir="auto"]').all()
                        for div in text_divs:
                            text = div.inner_text(timeout=500)
                            if text and text != name and len(text) > 1:
                                comment_text = text
                                break
                        
                        # 備用策略: 在同層附近找
                        if not comment_text:
                            nearby = self.page.locator(f'text=/{re.escape(name)}/').first
                            if nearby:
                                container = nearby.locator('xpath=../../..')
                                text_elem = container.locator('div[dir="auto"]').first
                                comment_text = text_elem.inner_text(timeout=500)
                    except:
                        pass
                    
                    # 清理留言內容
                    comment_text = comment_text.strip()[:500] if comment_text else ""
                    
                    comment_data = {
                        'search_keyword': keyword,
                        'post_url': post_url,
                        'post_title': post_title,
                        'commenter_name': name,
                        'commenter_profile_url': profile_url,
                        'comment_text': comment_text,
                        'comment_time': ''
                    }
                    
                    comments.append(comment_data)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"  ❌ 提取留言出錯: {e}")
        
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
    print("📘 Facebook 留言爬蟲")
    print("="*70)
    print("目標：搜尋「汽車保險」「港車北上」貼文，提取留言者資料\n")
    
    # 初始化數據庫
    conn, cursor = init_database()
    
    # 啟動爬蟲
    crawler = FacebookCrawler()
    crawler.start()
    
    try:
        # 檢查登入狀態
        if not crawler.check_login_status():
            if not crawler.manual_login():
                print("❌ 登入失敗，程序結束")
                return
        
        # 處理每個關鍵字
        total_comments = 0
        
        for keyword in CONFIG['SEARCH_KEYWORDS']:
            # 搜尋貼文
            posts = crawler.search_posts(keyword)
            
            # 處理每個貼文
            for idx, post in enumerate(posts, 1):
                print(f"\n  📄 處理第 {idx}/{len(posts)} 個貼文...")
                
                # 提取留言
                comments = crawler.extract_comments(post['url'], keyword)
                
                # 保存到數據庫
                saved_count = 0
                for comment in comments:
                    if save_comment(cursor, conn, comment):
                        saved_count += 1
                
                total_comments += saved_count
                print(f"    ✅ 保存 {saved_count} 條留言")
                
                # 短暫休息，避免被限制
                time.sleep(2)
        
        # 導出Excel
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 爬蟲完成！")
        print("="*70)
        print(f"📊 本次新增: {total_comments} 條留言")
        print(f"📊 數據庫總計: {total_records} 條")
        print(f"📁 Excel導出: {CONFIG['EXCEL_PATH']}")
        print(f"💾 數據庫: {CONFIG['DB_PATH']}")
        
    finally:
        crawler.close()
        conn.close()

if __name__ == '__main__':
    main()
