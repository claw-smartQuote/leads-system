#!/usr/bin/env python3
"""
Facebook 爬蟲 - 智能動態版 v6.0
修復問題：
1. 動態發現新帖子（不再寫死URL）
2. 去重機制（SQLite記錄已處理URL）
3. 強制滾動加载新內容
4. Stealth 模式突破反爬
5. 持久化登入狀態
6. 隨機延遲模擬真人
"""

import re
import sqlite3
import json
import time
import random
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, parse_qs, unquote

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError

# 嘗試導入 stealth插件
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
    print("✅ playwright-stealth 可用")
except ImportError:
    STEALTH_AVAILABLE = False
    print("⚠️ playwright-stealth 不可用，將使用手動反檢測")

# ==================== 設定 ====================
CONFIG = {
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_v6.db'),
    'PROCESSED_URLS_PATH': Path('/Users/claw/.openclaw/workspace/fb_processed_urls.json'),
    'EXCEL_PATH': Path(f'/Users/claw/.openclaw/workspace/fb_潛客_{datetime.now().strftime("%Y%m%d")}.xlsx'),
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
    'CREDS_PATH': Path.home() / '.fb_crawler' / 'fb_credentials.json',
    
    # 目標群組列表（可添加多個）
    'TARGET_GROUPS': [
        'https://www.facebook.com/groups/hkdrivers',
        'https://www.facebook.com/groups/hkcar',
        'https://www.facebook.com/groups/香港車友會',
        'https://www.facebook.com/groups/hongkongrab',
    ],
    
    # 每次最多處理新帖子數
    'MAX_NEW_POSTS': 10,
    'MAX_COMMENTS_PER_POST': 50,
}

# ==================== 數據庫 ====================
def init_database():
    """初始化數據庫"""
    CONFIG['DB_PATH'].parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    # 留言表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT UNIQUE,
            post_title TEXT,
            commenter_name TEXT,
            commenter_profile_url TEXT,
            comment_text TEXT,
            scraped_at TEXT
        )
    ''')
    
    # 已處理URL表（去重）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_urls (
            url TEXT PRIMARY KEY,
            processed_at TEXT,
            post_title TEXT
        )
    ''')
    
    conn.commit()
    return conn, cursor

def load_processed_urls():
    """載入已處理的URL集合"""
    try:
        if CONFIG['PROCESSED_URLS_PATH'].exists():
            with open(CONFIG['PROCESSED_URLS_PATH'], 'r') as f:
                data = json.load(f)
                return set(data.get('urls', []))
    except:
        pass
    return set()

def save_processed_urls(urls):
    """保存已處理的URL"""
    with open(CONFIG['PROCESSED_URLS_PATH'], 'w') as f:
        json.dump({'urls': list(urls), 'updated_at': datetime.now().isoformat()}, f)

def is_url_processed(cursor, url):
    """檢查URL是否已處理"""
    cursor.execute('SELECT 1 FROM processed_urls WHERE url = ?', (url,))
    return cursor.fetchone() is not None

def mark_url_processed(cursor, conn, url, post_title=''):
    """標記URL已處理"""
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO processed_urls (url, processed_at, post_title)
            VALUES (?, ?, ?)
        ''', (url, datetime.now().isoformat(), post_title[:200]))
        conn.commit()
    except Exception as e:
        pass

def save_lead(cursor, conn, data):
    """保存留言"""
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO fb_leads 
            (post_url, post_title, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['post_url'], data.get('post_title', ''),
            data['commenter_name'], data['commenter_profile_url'],
            data['comment_text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        return False

def export_to_excel(cursor):
    """導出到Excel"""
    cursor.execute('SELECT commenter_name, commenter_profile_url, comment_text, post_url, post_title, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者', '個人連結', '留言內容', '帖子連結', '帖子標題', '抓取時間'])
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

# ==================== Facebook 爬蟲 ====================
class FacebookCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def _random_delay(self, min_sec=3, max_sec=8):
        """隨機延遲"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        
    def _human_scroll(self, scrolls=5):
        """模擬人類滾動"""
        for _ in range(scrolls):
            scroll_amt = random.randint(400, 1000)
            self.page.evaluate(f'window.scrollBy(0, {scroll_amt})')
            self._random_delay(1.5, 3.0)
            
    def _move_mouse_human(self):
        """模擬人類滑鼠移動"""
        try:
            start_x = random.randint(100, 800)
            start_y = random.randint(200, 600)
            end_x = start_x + random.randint(-200, 200)
            end_y = start_y + random.randint(-100, 100)
            self.page.mouse.move(start_x, start_y)
            time.sleep(0.2)
            self.page.mouse.move(end_x, end_y)
        except:
            pass

    def start(self):
        """啟動瀏覽器"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(
            headless=False,
            slow_mo=random.randint(500, 1000),
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        
        # 創建上下文
        storage_state = str(CONFIG['STORAGE_STATE_PATH']) if CONFIG['STORAGE_STATE_PATH'].exists() else None
        
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-HK',
            timezone_id='Asia/Hong_Kong',
            extra_http_headers={
                'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        )
        
        # 添加反檢測腳本
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-HK', 'zh', 'en'] });
            window.chrome = { runtime: {} };
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_String;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Iterable;
        """)
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)
        
        # 如果有 stealth 插件，應用它
        if STEALTH_AVAILABLE:
            stealth_instance = Stealth()
            stealth_instance.apply_stealth_sync(self.page)
            print("  🎭 Stealth 模式已啟用")

    def check_login(self):
        """檢查登入狀態"""
        try:
            self.page.goto('https://www.facebook.com', timeout=30000, wait_until='domcontentloaded')
            self._random_delay(2, 4)
            
            # 檢查是否登入
            login_text = self.page.inner_text('body')
            if '登入' in login_text and '註冊' in login_text:
                print("  ⚠️ 未登入 Facebook")
                return False
            
            # 檢查登入按鈕是否存在
            try:
                self.page.wait_for_selector('#loginbutton', timeout=3000)
                print("  ⚠️ 未登入（發現登入按鈕）")
                return False
            except:
                pass
                
            print("  ✅ 已登入 Facebook")
            return True
        except Exception as e:
            print(f"  ❌ 登入檢查失敗: {e}")
            return False

    def auto_login(self):
        """自動登入"""
        creds = None
        if CONFIG['CREDS_PATH'].exists():
            with open(CONFIG['CREDS_PATH'], 'r') as f:
                creds = json.load(f)
        
        if not creds:
            print("  ❌ 無憑證，請先設置 fb_auto_login.py")
            return False
        
        print(f"  🔑 使用憑證: {creds.get('email', 'unknown')}")
        
        try:
            self.page.goto('https://www.facebook.com', timeout=60000)
            self._random_delay(2, 4)
            
            # 填入電郵
            self.page.fill('#email', creds['email'])
            self._random_delay(0.5, 1.5)
            
            # 填入密碼
            self.page.fill('#pass', creds['password'])
            self._random_delay(0.5, 1.5)
            
            # 點擊登入
            self._move_mouse_human()
            self.page.click('button[name="login"]')
            self._random_delay(3, 6)
            
            # 等待登入完成
            self.page.wait_for_url('**/home.php**', timeout=30000)
            
            # 保存登入狀態
            self.context.storage_state(path=str(CONFIG['STORAGE_STATE_PATH']))
            print("  ✅ 登入成功並保存狀態")
            return True
            
        except Exception as e:
            print(f"  ❌ 登入失敗: {e}")
            return False

    def discover_posts_from_group(self, group_url, cursor, limit=10):
        """從群組發現新帖子"""
        print(f"\n🔍 探索群組: {group_url[:60]}...")
        
        try:
            self.page.goto(group_url, timeout=60000, wait_until='domcontentloaded')
            self._random_delay(3, 5)
            
            # 滾動加載多次
            for i in range(random.randint(3, 6)):
                self._human_scroll(3)
                print(f"    滾動 {i+1}/6...")
                
            # 尋找帖子連結
            post_urls = []
            seen = set()
            
            # 策略1: 尋找 article 元素中的連結
            articles = self.page.locator('[role="article"]').all()
            print(f"    找到 {len(articles)} 個帖子區塊")
            
            for article in articles[:limit * 2]:
                try:
                    # 找主要連結 - 包含 /posts/ 的才是帖子
                    links = article.locator('a[href*="/posts/"]').all()
                    for link in links:
                        href = link.get_attribute('href', timeout=500) or ''
                        
                        # 過濾有效的帖子URL
                        if '/posts/' in href and 'facebook.com' in href:
                            # 清理URL引數
                            clean_url = re.sub(r'\?.*$', '', href.split('&__cft')[0])
                            if clean_url not in seen:
                                seen.add(clean_url)
                                # 檢查是否已處理
                                if not is_url_processed(cursor, clean_url):
                                    post_urls.append(clean_url)
                                    print(f"    🆕 新帖子: {clean_url[:60]}...")
                                    if len(post_urls) >= limit:
                                        break
                    if len(post_urls) >= limit:
                        break
                except Exception as e:
                    continue
                    
            # 策略2: 直接找具有帖子特徵的連結
            if len(post_urls) < 3:
                print("    嘗試備用策略...")
                all_links = self.page.locator('a[href*="/posts/"]').all()
                for link in all_links:
                    try:
                        href = link.get_attribute('href', timeout=300) or ''
                        if '/posts/' in href and 'facebook.com' in href and len(href) > 50:
                            clean_url = re.sub(r'\?.*$', '', href.split('&__cft')[0])
                            if clean_url not in seen:
                                seen.add(clean_url)
                                if not is_url_processed(cursor, clean_url):
                                    post_urls.append(clean_url)
                                    if len(post_urls) >= limit:
                                        break
                    except:
                        continue
            
            print(f"    📊 發現 {len(post_urls)} 個新帖子")
            return post_urls
            
        except Exception as e:
            print(f"    ❌ 探索失敗: {e}")
            return []

    def expand_comments(self):
        """展開所有留言"""
        max_attempts = 15
        for attempt in range(max_attempts):
            clicked = False
            
            # 找所有 "查看更多" 類型的按鈕
            selectors = [
                '[role="button"]:has-text("更多")',
                '[role="button"]:has-text("更多回覆")',
                '[role="button"]:has-text("View more")',
                '[role="button"]:has-text("查看更多")',
                '[role="button"]:has-text("其他回覆")',
                'div[style*="transform"] >> text=/更多|more/i',
            ]
            
            for selector in selectors:
                try:
                    buttons = self.page.locator(selector).all()
                    for btn in buttons:
                        try:
                            if btn.is_visible(timeout=500) and btn.is_enabled(timeout=500):
                                self._move_mouse_human()
                                btn.click(timeout=3000)
                                self._random_delay(1.5, 3)
                                clicked = True
                        except:
                            pass
                except:
                    pass
                    
            if not clicked:
                break
                
    def extract_comments(self, post_url):
        """提取帖子中的留言"""
        print(f"\n🌐 訪問帖子...")
        
        try:
            self.page.goto(post_url, timeout=90000, wait_until='domcontentloaded')
            self._random_delay(3, 5)
            
            # 滾動加載
            self._human_scroll(4)
            
            # 展開留言
            print("  展開留言...")
            self.expand_comments()
            self._human_scroll(2)
            
            # 提取留言
            comments = []
            seen_profiles = set()
            
            # 方法1: 使用 article 元素
            articles = self.page.locator('[role="article"]').all()
            print(f"  方法1: 找到 {len(articles)} 個 article")
            
            for article in articles:
                try:
                    # 找用戶連結 - 更寬鬆的匹配
                    user_links = article.locator('a[href*="facebook.com"]').all()
                    user_link = None
                    href = None
                    name = None
                    
                    for link in user_links:
                        href = link.get_attribute('href', timeout=300) or ''
                        name = link.inner_text(timeout=300).strip() or ''
                        
                        # 跳過無效連結
                        if not href or len(href) < 10:
                            continue
                        if any(x in href for x in ['/login', '/recover', '/help', '/privacy', '/l.php', '/groups/', '/pages/', '/photo', '/video', '/watch']):
                            continue
                        if '/user/' in href:
                            user_link = link
                            break
                        elif '/profile.php?id=' in href:
                            user_link = link
                            break
                        elif re.match(r'https://www\.facebook\.com/[a-zA-Z0-9._-]+/?$', href):
                            # 排除普通詞
                            username = href.replace('https://www.facebook.com/', '').replace('/', '')
                            if username and len(username) > 2 and username not in ['help', 'login', 'recover', 'settings', 'help']:
                                user_link = link
                                break
                    
                    if not user_link:
                        continue
                    
                    href = user_link.get_attribute('href', timeout=500) or ''
                    name = user_link.inner_text(timeout=500).strip()
                    
                    if not self._is_valid_user(href, name):
                        continue
                    
                    clean_url = self._clean_profile_url(href)
                    if not clean_url or clean_url in seen_profiles:
                        continue
                    seen_profiles.add(clean_url)
                    
                    # 提取留言內容 - 在 article 範圍內找文字
                    comment_text = ""
                    try:
                        # 找所有文字
                        all_texts = article.locator('div').all()
                        for div in all_texts:
                            try:
                                text = div.inner_text(timeout=200).strip()
                                # 有效文字條件
                                if text and len(text) > 5 and len(text) < 500:
                                    if text != name:
                                        # 排除表情和按鈕文字
                                        if not any(x in text for x in ['👍', '❤️', '😂', '😢', '😠', '🙁', '😮', '回覆', 'Reply', '查看', '分享', '更多', 'edited']):
                                            # 排除時間戳
                                            if not re.match(r'^\d+$', text) and '小時' not in text and '分鐘' not in text and '日' not in text and '年' not in text:
                                                comment_text = text[:500]
                                                break
                            except:
                                pass
                    except:
                        pass
                    
                    comments.append({
                        'post_url': post_url,
                        'commenter_name': name,
                        'commenter_profile_url': clean_url,
                        'comment_text': comment_text or "(無法提取)"
                    })
                    
                except Exception as e:
                    continue
            
            # 方法2: 如果方法1效果不好，使用更廣泛的搜索
            if len(comments) < 2:
                print(f"  方法2: 嘗試備用提取...")
                try:
                    # 找所有包含 /profile.php?id= 或 /user/ 的連結
                    all_profile_links = self.page.locator('a[href*="/profile.php?id="], a[href*="/user/"]').all()
                    print(f"    找到 {len(all_profile_links)} 個個人連結")
                    
                    for link in all_profile_links:
                        try:
                            href = link.get_attribute('href', timeout=300) or ''
                            name = link.inner_text(timeout=300).strip()
                            
                            if not self._is_valid_user(href, name):
                                continue
                            
                            clean_url = self._clean_profile_url(href)
                            if not clean_url or clean_url in seen_profiles:
                                continue
                            seen_profiles.add(clean_url)
                            
                            # 嘗試找附近的文字
                            comment_text = ""
                            try:
                                # 向上找父元素然後搜索文字
                                parent = link.locator('xpath=ancestor::div[2]')
                                texts = parent.locator('div[dir="auto"]').all()
                                for t in texts:
                                    txt = t.inner_text(timeout=200).strip()
                                    if txt and txt != name and len(txt) > 5:
                                        comment_text = txt[:500]
                                        break
                            except:
                                pass
                            
                            comments.append({
                                'post_url': post_url,
                                'commenter_name': name,
                                'commenter_profile_url': clean_url,
                                'comment_text': comment_text or "(無法提取)"
                            })
                        except:
                            continue
                except Exception as e:
                    print(f"    備用方法失敗: {e}")
            
            print(f"  📊 共提取 {len(comments)} 條留言")
            return comments[:CONFIG['MAX_COMMENTS_PER_POST']]
            
        except Exception as e:
            print(f"  ❌ 提取失敗: {e}")
            return []

    def _is_valid_user(self, href, name):
        """驗證用戶是否有效"""
        if not href:
            return False
        
        # 跳過明顯不是個人檔案的連結
        skip_patterns = ['/login', '/recover', '/help', '/privacy', '/l.php', '/photo', '/video', '/watch', '/marketplace']
        if any(x in href for x in skip_patterns):
            return False
        
        # 接受 /user/xxx 或 /profile.php?id=xxx 格式（即使在 groups 上下文裡也是用戶）
        if '/user/' in href or '/profile.php?id=' in href:
            # 名稱可選，但有的話要有效
            if name:
                if len(name) < 2 or len(name) > 50:
                    return False
                skip_names = ['讚', '回覆', 'Like', 'Reply', '更多', '分享', 'Comment', '登入', 'Facebook', '查看', 'recover', 'help']
                if any(x in name for x in skip_names):
                    return False
            return True
        
        # /groups/xxx/posts/yyy 是帖子不是用戶
        if '/groups/' in href and '/posts/' in href:
            return False
        
        return False  # 其他格式不處理

    def _clean_profile_url(self, href):
        """清理個人連結"""
        if not href:
            return None
        
        # 清理 __cft__ 參數
        clean_href = re.sub(r'\?.*$', '', href.split('&__cft')[0])
        
        # 處理 /groups/xxx/user/yyy/ 格式 -> 轉換為 profile URL
        user_match = re.search(r'/user/(\d+)', clean_href)
        if user_match:
            return f"https://www.facebook.com/profile.php?id={user_match.group(1)}"
        
        # 處理 profile.php?id=xxx 格式（只匹配完整格式）
        id_match = re.search(r'profile\.php\?id=(\d+)', clean_href)
        if id_match:
            return f"https://www.facebook.com/profile.php?id={id_match.group(1)}"
        
        return None  # 其他格式不處理，避免返回無效URL

    def close(self):
        """關閉瀏er器"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
        except:
            pass

# ==================== 主程序 ====================
def main():
    print("="*70)
    print("📘 Facebook 智能爬蟲 v6.0 - 動態版")
    print("="*70)
    print("✨ 新功能：")
    print("  • 動態探索群組新帖子")
    print("  • 去重機制（不重複處理）")
    print("  • Stealth 反檢測模式")
    print("  • 隨機延遲模擬真人")
    print()
    
    conn, cursor = init_database()
    processed_urls = load_processed_urls()
    print(f"📊 已處理 {len(processed_urls)} 個URL\n")
    
    crawler = FacebookCrawler()
    
    try:
        crawler.start()
        
        # 檢查/執行登入
        if not crawler.check_login():
            print("\n🔐 嘗試自動登入...")
            if not crawler.auto_login():
                print("\n❌ 無法登入，請先設置 FB 憑證")
                return
        
        total_new_posts = 0
        total_comments = 0
        all_new_posts = []
        
        # 從每個群組探索新帖子
        for group_url in CONFIG['TARGET_GROUPS']:
            new_posts = crawler.discover_posts_from_group(group_url, cursor, 
                                                         limit=CONFIG['MAX_NEW_POSTS'])
            all_new_posts.extend(new_posts)
            crawler._random_delay(5, 10)
        
        # 去重
        all_new_posts = list(set(all_new_posts))[:CONFIG['MAX_NEW_POSTS']]
        print(f"\n📊 共發現 {len(all_new_posts)} 個新帖子待處理")
        
        # 處理每個新帖子
        for i, post_url in enumerate(all_new_posts, 1):
            print(f"\n[{i}/{len(all_new_posts)}] 處理帖子...")
            
            # 提取留言
            comments = crawler.extract_comments(post_url)
            
            # 保存留言
            saved_count = 0
            for comment in comments:
                if save_lead(cursor, conn, comment):
                    saved_count += 1
                    print(f"    ✅ {comment['commenter_name']}: {comment['comment_text'][:40]}...")
            
            # 標記已處理
            mark_url_processed(cursor, conn, post_url)
            processed_urls.add(post_url)
            
            total_comments += saved_count
            total_new_posts += 1
            
            # 隨機休息
            crawler._random_delay(5, 15)
        
        # 保存已處理URL
        save_processed_urls(processed_urls)
        
        # 導出
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 爬蟲完成！")
        print("="*70)
        print(f"📊 新帖子: {total_new_posts} 個")
        print(f"📊 新留言: {total_comments} 條")
        print(f"📊 數據庫總計: {total_records} 條")
        print(f"📁 Excel: {CONFIG['EXCEL_PATH']}")
        
        # 顯示最新5條
        if total_comments > 0:
            print("\n📋 最新抓取的 5 條留言：")
            cursor.execute("SELECT commenter_name, comment_text, post_url FROM fb_leads ORDER BY scraped_at DESC LIMIT 5")
            for row in cursor.fetchall():
                print(f"  • {row[0]}: {row[1][:50]}...")
                print(f"    🔗 {row[2][:60]}...")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        crawler.close()
        conn.close()
        print("\n👋 完成")

if __name__ == '__main__':
    main()
