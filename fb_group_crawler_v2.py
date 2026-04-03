#!/usr/bin/env python3
"""
Facebook 群組智能爬蟲 v2.0
功能：
  - 自動探索群組內新帖子
  - 去重機制（SQLite 記錄已處理 URL）
  - Stealth 模式繞過反爬
  - 持久化登入狀態
  - 模擬真人行為
"""

import re
import sqlite3
import json
import time
import random
import hashlib
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ==================== 配置 ====================
CONFIG = {
    # 目標群組列表
    'GROUP_URLS': [
        'https://www.facebook.com/groups/hkdrivers/',
        'https://www.facebook.com/groups/hkcar/',
        'https://www.facebook.com/groups/28carhk/',
    ],
    
    # 每次爬取最多新帖子數
    'MAX_NEW_POSTS_PER_RUN': 5,
    
    # 數據庫路徑
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_group_leads.db'),
    'PROCESSED_POSTS_DB': Path('/Users/claw/.openclaw/workspace/fb_processed_posts.json'),
    'EXCEL_PATH': Path(f'/Users/claw/.openclaw/workspace/fb_群組潛客_{datetime.now().strftime("%Y%m%d")}.xlsx'),
    
    # FB 登入狀態
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
    'USER_DATA_DIR': Path.home() / '.fb_crawler' / 'facebook_data',
    
    # 隨機延遲範圍（秒）
    'DELAY_MIN': 3,
    'DELAY_MAX': 8,
}

# ==================== 工具函數 ====================
def random_delay():
    """隨機延遲，模擬真人操作"""
    delay = random.uniform(CONFIG['DELAY_MIN'], CONFIG['DELAY_MAX'])
    print(f"    ⏱️ 等待 {delay:.1f}s...")
    time.sleep(delay)

def random_scroll(page):
    """隨機滾動頁面"""
    scroll_amount = random.randint(500, 1200)
    page.evaluate(f'window.scrollBy(0, {scroll_amount})')

def get_post_hash(url):
    """生成帖子唯一哈希"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

# ==================== 去重機制 ====================
class PostDeduplicator:
    def __init__(self, db_path):
        self.db_path = db_path
        self.processed = self._load()
    
    def _load(self):
        """從 JSON 檔案載入已處理帖子"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    print(f"📋 已載入 {len(data)} 個已處理帖子")
                    return set(data)
            except:
                pass
        return set()
    
    def save(self):
        """保存已處理帖子到 JSON"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(list(self.processed), f, indent=2)
    
    def is_processed(self, url):
        """檢查帖子是否已處理"""
        return get_post_hash(url) in self.processed
    
    def mark_processed(self, url):
        """標記帖子為已處理"""
        self.processed.add(get_post_hash(url))
        self.save()

# ==================== 數據庫 ====================
def init_database():
    CONFIG['DB_PATH'].parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    # 帖子表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_hash TEXT UNIQUE,
            post_url TEXT,
            post_text TEXT,
            group_name TEXT,
            scraped_at TEXT
        )
    ''')
    
    # 留言者表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_hash TEXT,
            commenter_name TEXT,
            commenter_profile_url TEXT,
            comment_text TEXT,
            scraped_at TEXT,
            FOREIGN KEY (post_hash) REFERENCES fb_posts(post_hash)
        )
    ''')
    
    conn.commit()
    return conn, cursor

def save_post(cursor, conn, post_url, post_text, group_name):
    """保存帖子"""
    post_hash = get_post_hash(post_url)
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO fb_posts (post_hash, post_url, post_text, group_name, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (post_hash, post_url, post_text[:500] if post_text else "", group_name,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return post_hash
    except Exception as e:
        print(f"  ⚠️ 保存帖子失敗: {e}")
        return None

def save_leads(cursor, conn, post_hash, comments):
    """批量保存留言"""
    saved = 0
    for comment in comments:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO fb_leads 
                (post_hash, commenter_name, commenter_profile_url, comment_text, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (post_hash, comment['name'], comment['profile_url'],
                  comment['text'][:500] if comment['text'] else "", 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            if cursor.rowcount > 0:
                saved += 1
        except Exception as e:
            pass
    conn.commit()
    return saved

def export_to_excel(cursor):
    """導出到 Excel"""
    import pandas as pd
    cursor.execute('''
        SELECT l.commenter_name, l.commenter_profile_url, l.comment_text, 
               p.post_text, p.group_name, p.scraped_at
        FROM fb_leads l
        JOIN fb_posts p ON l.post_hash = p.post_hash
        ORDER BY l.scraped_at DESC
    ''')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者', '個人連結', '留言內容', '帖子摘要', '群組', '抓取時間'])
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

# ==================== Facebook 爬蟲 ====================
class FacebookGroupCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    def start(self):
        """啟動瀏覽器"""
        self.playwright = sync_playwright().start()
        
        # 嘗試使用持久化上下文（真實用戶數據）
        user_data_dir = str(CONFIG['USER_DATA_DIR'])
        
        try:
            # 先嘗試使用真實用戶目錄
            if CONFIG['USER_DATA_DIR'].exists():
                print(f"🔑 使用持久化用戶目錄: {user_data_dir}")
                self.browser = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=True,
                    slow_mo=100,
                    viewport={'width': 1400, 'height': 900},
                    locale='zh-HK',
                    timezone_id='Asia/Hong_Kong',
                )
                self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
                return
        except Exception as e:
            print(f"⚠️ 持久化上下文失敗: {e}")
        
        # 回退：使用標準備份登入狀態
        print("🔑 使用 Cookie 登入狀態")
        self.browser = self.playwright.chromium.launch(
            headless=True,  # 改為無頭模式
            slow_mo=100,  # 減慢操作速度
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-browsing-history',
                '--media-cache-size=0',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        
        # 加載 Cookie
        storage_state = None
        if CONFIG['STORAGE_STATE_PATH'].exists():
            storage_state = str(CONFIG['STORAGE_STATE_PATH'])
        
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='zh-HK',
            timezone_id='Asia/Hong_Kong',
        )
        
        # Stealth 腳本
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-HK', 'zh', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            delete navigator.__proto__.__proto__;
        """)
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)
    
    def check_login(self):
        """檢查是否已登入"""
        try:
            self.page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=15000)
            random_delay()
            
            # 檢查登入標記 - 查找登入表單
            login_form = self.page.locator('form[action*="login"]').count()
            if login_form > 0:
                print("❌ 未登入 Facebook（發現登入表單）")
                return False
            
            # 檢查是否有帖子內容（已登入用戶會看到首頁資訊流）
            # 找「在想什麼？」輸入框（已登入用戶可見）
            composer = self.page.locator('[aria-label="在想些什麼？"]').count()
            if composer == 0:
                composer = self.page.locator('[aria-label*="在想"]').count()
            
            if composer > 0:
                print("✅ Facebook 已登入（發現動態時報）")
                return True
            
            # 備用：檢查 Cookies
            try:
                fb_cookies = self.context.cookies(['https://facebook.com'])
                c_user = any(c['name'] == 'c_user' for c in fb_cookies)
                if c_user:
                    print("✅ Facebook 已登入（Cookie 驗證）")
                    return True
            except:
                pass
                
            print("⚠️ 無法確認登入狀態，繼續嘗試...")
            return True
            
        except Exception as e:
            print(f"❌ 登入檢查失敗: {e}")
            return False
    
    def save_login_state(self):
        """保存登入狀態"""
        try:
            CONFIG['STORAGE_STATE_PATH'].parent.mkdir(parents=True, exist_ok=True)
            self.context.storage_state(path=str(CONFIG['STORAGE_STATE_PATH']))
            print("✅ 登入狀態已保存")
        except Exception as e:
            print(f"⚠️ 保存登入狀態失敗: {e}")
    
    def discover_posts_from_group(self, group_url):
        """
        從群組頁面發現新帖子
        滾動頁面，加載新內容，返回帖子 URL 列表
        """
        print(f"\n🔍 探索群組: {group_url[:60]}...")
        
        try:
            self.page.goto(group_url, wait_until='domcontentloaded', timeout=30000)
            random_delay()
            
            # 滾動加載新內容
            print("  📜 滾動頁面加載新帖子...")
            for i in range(random.randint(3, 5)):
                random_scroll(self.page)
                random_delay()
            
            # 提取帖子連結
            post_urls = []
            seen_urls = set()
            
            # 方法1: 找帖子 article 元素
            articles = self.page.locator('[role="article"]').all()
            print(f"    找到 {len(articles)} 個帖子區塊")
            
            for article in articles:
                try:
                    # 在 article 內找連結
                    links = article.locator('a[href*="facebook.com"]').all()
                    for link in links:
                        try:
                            href = link.get_attribute('href', timeout=300) or ''
                            # 過濾有效的帖子連結
                            if '/groups/' in href and ('?__cft__' in href or '/posts/' in href or '/permalink/' in href):
                                # 清理 URL
                                clean_url = re.sub(r'\?__cft__.*$', '', href.split('?')[0])
                                if clean_url and clean_url not in seen_urls:
                                    seen_urls.add(clean_url)
                                    post_urls.append(clean_url)
                        except:
                            pass
                except:
                    pass
            
            # 方法2: 直接找文字包含帖子的連結
            if len(post_urls) < 3:
                all_links = self.page.locator(f'a[href*="{group_url.split("/")[-1]}"]').all()
                for link in all_links:
                    try:
                        href = link.get_attribute('href', timeout=200) or ''
                        if '/groups/' in href and '/posts/' in href:
                            clean_url = re.sub(r'\?__cft__.*$', '', href.split('?')[0])
                            if clean_url and clean_url not in seen_urls:
                                seen_urls.add(clean_url)
                                post_urls.append(clean_url)
                    except:
                        pass
            
            # 去重
            post_urls = list(set(post_urls))
            print(f"    📋 發現 {len(post_urls)} 個帖子連結")
            
            return post_urls
            
        except Exception as e:
            print(f"    ❌ 探索失敗: {e}")
            return []
    
    def extract_comments_from_post(self, post_url):
        """
        從單個帖子提取留言
        """
        print(f"\n  📄 提取帖子: {post_url[:60]}...")
        
        try:
            self.page.goto(post_url, wait_until='domcontentloaded', timeout=60000)
            random_delay()
            
            # 滾動加載留言
            print("    📜 滾動加載留言...")
            for _ in range(random.randint(2, 4)):
                random_scroll(self.page)
                random_delay()
            
            # 展開「查看更多留言」
            self._expand_comments()
            
            # 再滾動
            for _ in range(random.randint(1, 2)):
                random_scroll(self.page)
                random_delay()
            
            # 提取留言
            comments = []
            seen_profiles = set()
            
            # 策略1: article 元素
            articles = self.page.locator('[role="article"]').all()
            print(f"    找到 {len(articles)} 個留言區塊")
            
            for article in articles:
                try:
                    # 找用戶連結
                    user_link = article.locator('a[href*="facebook.com/"]').first
                    if user_link.count() == 0:
                        continue
                    
                    href = user_link.get_attribute('href', timeout=500) or ''
                    name = user_link.inner_text(timeout=500).strip()
                    
                    # 過濾
                    if not self._is_valid_user(href, name):
                        continue
                    
                    clean_url = self._clean_profile_url(href)
                    if not clean_url or clean_url in seen_profiles:
                        continue
                    seen_profiles.add(clean_url)
                    
                    # 提取留言文字
                    comment_text = ""
                    try:
                        text_divs = article.locator('div[dir="auto"]').all()
                        for div in text_divs:
                            text = div.inner_text(timeout=200).strip()
                            if text and text != name and len(text) > 3:
                                if text not in ['讚', '回覆', 'Like', 'Reply', '更多', '愛心', '查看翻譯']:
                                    comment_text = text
                                    break
                    except:
                        pass
                    
                    if comment_text:
                        comments.append({
                            'name': name,
                            'profile_url': clean_url,
                            'text': comment_text
                        })
                        print(f"      ✅ {name}: {comment_text[:40]}...")
                        
                except Exception as e:
                    continue
            
            return comments
            
        except Exception as e:
            print(f"    ❌ 提取失敗: {e}")
            return []
    
    def _expand_comments(self):
        """展開所有留言（點擊查看更多）"""
        max_clicks = 15
        clicked_count = 0
        
        for _ in range(max_clicks):
            clicked = False
            
            # 找所有可點擊的「更多」按鈕
            try:
                buttons = self.page.locator('[role="button"]').all()
                for btn in buttons:
                    try:
                        text = btn.inner_text(timeout=300).lower()
                        if any(k in text for k in ['更多', 'more', 'view', '則回覆', 'replies']):
                            if btn.is_visible() and btn.is_enabled():
                                btn.click()
                                random_delay()
                                clicked = True
                                clicked_count += 1
                                print(f"      💬 展開留言 ({clicked_count})")
                                break
                    except:
                        pass
            except:
                pass
            
            if not clicked:
                break
        
        if clicked_count > 0:
            print(f"      共展開 {clicked_count} 個留言線程")
    
    def _is_valid_user(self, href, name):
        """驗證用戶是否有效"""
        if not href or not name or len(name) < 2:
            return False
        if len(name) > 50:
            return False
        if name in ['讚', '回覆', 'Like', 'Reply', '更多', '分享', 'Comment', '登入', 'Facebook']:
            return False
        if any(x in href for x in ['/login', '/recover', '/help', '/privacy', '/l.php', 'watch']):
            return False
        return True
    
    def _clean_profile_url(self, href):
        """清理個人連結"""
        if not href:
            return None
        
        # profile.php?id=xxx
        if '/profile.php?id=' in href:
            match = re.search(r'id=(\d+)', href)
            if match:
                return f"https://www.facebook.com/profile.php?id={match.group(1)}"
        
        # /username 格式
        match = re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)', href)
        if match:
            username = match.group(1)
            if username not in ['login', 'recover', 'help', 'watch', 'marketplace', 'groups', 'pages', 'photo', 'photo.php', 'story.php']:
                return f"https://www.facebook.com/{username}"
        
        return None
    
    def close(self):
        """關閉瀏覽器"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass

# ==================== 主程序 ====================
def main():
    print("="*70)
    print("📘 Facebook 群組智能爬蟲 v2.0")
    print("="*70)
    print("功能：自動探索 + 去重 + Stealth 模式\n")
    
    # 初始化
    dedup = PostDeduplicator(CONFIG['PROCESSED_POSTS_DB'])
    conn, cursor = init_database()
    crawler = FacebookGroupCrawler()
    
    try:
        # 啟動瀏覽器
        crawler.start()
        
        # 檢查登入
        if not crawler.check_login():
            print("\n❌ 需要登入 Facebook")
            print("請運行：python3 fb_login.py")
            return
        
        # 保存登入狀態
        crawler.save_login_state()
        
        # 收集所有新帖子
        all_new_posts = []
        
        for group_url in CONFIG['GROUP_URLS']:
            post_urls = crawler.discover_posts_from_group(group_url)
            
            # 過濾未處理的帖子
            new_posts = [url for url in post_urls if not dedup.is_processed(url)]
            print(f"    🆕 新帖子: {len(new_posts)}/{len(post_urls)}")
            
            all_new_posts.extend([(url, group_url) for url in new_posts])
            
            # 避免請求過快
            random_delay()
        
        print(f"\n📊 總共發現 {len(all_new_posts)} 個新帖子")
        
        if len(all_new_posts) == 0:
            print("✅ 沒有新帖子需要處理")
            return
        
        # 限制處理的帖子數量
        all_new_posts = all_new_posts[:CONFIG['MAX_NEW_POSTS_PER_RUN']]
        print(f"📝 本次處理 {len(all_new_posts)} 個帖子\n")
        
        # 處理每個帖子
        total_leads = 0
        
        for idx, (post_url, group_name) in enumerate(all_new_posts, 1):
            print(f"\n{'='*50}")
            print(f"📄 [{idx}/{len(all_new_posts)}] 處理帖子")
            print(f"{'='*50}")
            
            # 提取留言
            comments = crawler.extract_comments_from_post(post_url)
            
            # 保存帖子
            post_hash = save_post(cursor, conn, post_url, "", group_name)
            
            if post_hash and comments:
                # 保存留言
                saved = save_leads(cursor, conn, post_hash, comments)
                total_leads += saved
                print(f"  📊 保存 {saved} 條留言")
            else:
                print(f"  📊 沒有新留言")
            
            # 標記為已處理
            dedup.mark_processed(post_url)
            
            # 避免請求過快
            if idx < len(all_new_posts):
                random_delay()
        
        # 導出 Excel
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 爬蟲完成！")
        print("="*70)
        print(f"📊 本次新增留言: {total_leads} 條")
        print(f"📊 數據庫總計: {total_records} 條")
        print(f"📁 Excel導出: {CONFIG['EXCEL_PATH']}")
        print(f"📋 已處理帖子: {len(dedup.processed)} 個")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        crawler.close()
        conn.close()
        print("\n👋 爬蟲已結束")

if __name__ == '__main__':
    main()
