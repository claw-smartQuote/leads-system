#!/usr/bin/env python3
"""
Facebook 留言爬蟲 - 智能語義定位版 v5.0
技術方案：Playwright + 結構化選擇器 + Cookie狀態保持
"""

import re
import sqlite3
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

# ==================== 設定 ====================
CONFIG = {
    # 目標貼文URL列表（可添加多個）
    'POST_URLS': [
        'https://www.facebook.com/share/p/1DrEnCiSTY/',
    ],
    
    # 數據庫路徑
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_final.db'),
    'EXCEL_PATH': Path(f'/Users/claw/.openclaw/workspace/fb_潛客_{datetime.now().strftime("%Y%m%d")}.xlsx'),
    
    # 登入狀態路徑
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
            (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
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
        SELECT commenter_name, commenter_profile_url, comment_text, post_url, scraped_at 
        FROM fb_leads ORDER BY scraped_at DESC
    ''')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

# ==================== Facebook 智能爬蟲 ====================
class FacebookSmartCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        """啟動瀏覽器並加載登入狀態"""
        playwright = sync_playwright().start()
        
        # 啟動瀏覽器（非無頭模式，方便調試）
        self.browser = playwright.chromium.launch(
            headless=False, user_data_dir="/Users/claw/.openclaw/browser/openclaw/user-data",
            slow_mo=800,  # 操作延遲，模擬真人
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # 加載登入狀態
        storage_state = None
        if CONFIG['STORAGE_STATE_PATH'].exists():
            print(f"🔑 加載登入狀態: {CONFIG['STORAGE_STATE_PATH']}")
            storage_state = str(CONFIG['STORAGE_STATE_PATH'])
        
        # 創建瀏覽器上下文
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-HK',
            timezone_id='Asia/Hong_Kong',
        )
        
        # 隱藏自動化痕跡
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = self.context.new_page()
        
        # 設置超時
        self.page.set_default_timeout(60000)
        
    def simulate_human_behavior(self):
        """模擬真人行為：滾動頁面"""
        import random
        import time
        
        # 隨機滾動多次
        for _ in range(random.randint(5, 10)):
            scroll_amount = random.randint(600, 1200)
            self.page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            time.sleep(random.uniform(1.5, 3.0))
            
    def expand_all_comments(self):
        """智能展開所有留言"""
        import time
        
        max_attempts = 20
        for attempt in range(max_attempts):
            clicked = False
            
            # 策略1: 找包含特定文字的按鈕
            try:
                # 使用更寬鬆的文本匹配
                buttons = self.page.locator('[role="button"]').all()
                for btn in buttons:
                    try:
                        text = btn.inner_text(timeout=500).lower()
                        # 匹配各種語言的「查看更多」
                        if any(k in text for k in ['更多', 'more', 'view', '則', 'comment']):
                            # 確保不是輸入框或其他元素
                            if btn.is_visible() and btn.is_enabled():
                                btn.click()
                                time.sleep(2)
                                clicked = True
                                print(f"    展開留言...")
                                break
                    except:
                        pass
            except:
                pass
            
            if not clicked:
                break
                
    def extract_comments_semantic(self, post_url):
        """
        使用語義定位提取留言
        策略：role="article" 區塊通常包含一條完整留言
        """
        import time
        
        print(f"\n🌐 訪問貼文: {post_url[:50]}...")
        
        # 訪問頁面
        self.page.goto(post_url, wait_until='networkidle', timeout=90000)
        time.sleep(5)
        
        # 模擬真人滾動
        print("  滾動加載內容...")
        self.simulate_human_behavior()
        
        # 展開所有留言
        print("  展開所有留言...")
        self.expand_all_comments()
        
        # 再次滾動確保加載完成
        self.simulate_human_behavior()
        
        print("  提取留言資料...")
        comments = []
        seen_profiles = set()
        
        # ===== 策略1: 使用 role="article" 定位留言區塊 =====
        try:
            articles = self.page.locator('[role="article"]').all()
            print(f"    找到 {len(articles)} 個 article 區塊")
            
            for article in articles:
                try:
                    # 在article內找用戶連結
                    user_link = article.locator('a[href*="facebook.com"]').first
                    if user_link.count() == 0:
                        continue
                    
                    href = user_link.get_attribute('href', timeout=500) or ''
                    name = user_link.inner_text(timeout=500).strip()
                    
                    # 篩選有效用戶
                    if not self._is_valid_user(href, name):
                        continue
                    
                    # 清理URL
                    clean_url = self._clean_profile_url(href)
                    if not clean_url or clean_url in seen_profiles:
                        continue
                    seen_profiles.add(clean_url)
                    
                    # 提取留言內容 - 使用 dir="auto" 定位文字
                    comment_text = ""
                    try:
                        # 在article內找所有文字段落
                        text_divs = article.locator('div[dir="auto"]').all()
                        for div in text_divs:
                            text = div.inner_text(timeout=300).strip()
                            # 排除用戶名和常見按鈕文字
                            if text and text != name and len(text) > 2:
                                if text not in ['讚', '回覆', 'Like', 'Reply', '更多', '愛心']:
                                    comment_text = text
                                    break
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
                    
        except Exception as e:
            print(f"    article策略失敗: {e}")
        
        # ===== 策略2: 如果article策略效果不佳，使用備用策略 =====
        if len(comments) < 3:
            print("    使用備用策略...")
            comments = self._extract_fallback(seen_profiles, post_url)
        
        return comments
    
    def _is_valid_user(self, href, name):
        """檢查是否為有效用戶"""
        if not href or not name:
            return False
        if len(name) < 2 or len(name) > 40:
            return False
        if name in ['讚', '回覆', 'Like', 'Reply', '更多', '分享', 'Comment', '登入', '忘記帳戶']:
            return False
        if any(x in href for x in ['/login', '/recover', '/help', '/privacy', '/l.php']):
            return False
        return True
    
    def _clean_profile_url(self, href):
        """清理用戶URL"""
        if not href:
            return None
            
        # 處理 profile.php?id=xxx 格式
        if '/profile.php?id=' in href:
            match = re.search(r'id=(\d+)', href)
            if match:
                return f"https://www.facebook.com/profile.php?id={match.group(1)}"
        
        # 處理 /username 格式
        match = re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)', href)
        if match:
            username = match.group(1)
            if username not in ['login', 'recover', 'help', 'watch', 'marketplace', 'groups']:
                return f"https://www.facebook.com/{username}"
        
        return None
    
    def _extract_fallback(self, seen_profiles, post_url):
        """備用提取策略"""
        comments = []
        
        try:
            # 找所有連結
            all_links = self.page.locator('a[href*="facebook.com"]').all()
            
            for link in all_links:
                try:
                    href = link.get_attribute('href', timeout=200) or ''
                    name = link.inner_text(timeout=300).strip()
                    
                    if not self._is_valid_user(href, name):
                        continue
                    
                    clean_url = self._clean_profile_url(href)
                    if not clean_url or clean_url in seen_profiles:
                        continue
                    seen_profiles.add(clean_url)
                    
                    # 嘗試在同層級附近找文字內容
                    comment_text = ""
                    try:
                        parent = link.locator('xpath=ancestor::div[4]')
                        texts = parent.locator('div[dir="auto"]').all()
                        for t in texts:
                            txt = t.inner_text(timeout=200).strip()
                            if txt and txt != name and len(txt) > 2:
                                comment_text = txt
                                break
                    except:
                        pass
                    
                    comments.append({
                        'post_url': post_url,
                        'commenter_name': name,
                        'commenter_profile_url': clean_url,
                        'comment_text': comment_text[:500] if comment_text else "(無法提取)"
                    })
                    
                except:
                    pass
                    
        except Exception as e:
            print(f"    備用策略失敗: {e}")
        
        return comments
    
    def close(self):
        """關閉瀏覽器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

# ==================== 自動登入檢查 ====================
def check_fb_login():
    """自動檢查並刷新 FB 登入狀態"""
    storage_path = Path.home() / '.fb_crawler' / 'fb_storage_state.json'
    
    if not storage_path.exists():
        print("⚠️ 未找到 FB 登入狀態，正在啟動自動登入...")
        return False
    
    try:
        with open(storage_path, 'r') as f:
            state = json.load(f)
        
        cookies = state.get('cookies', [])
        c_user = next((c for c in cookies if c.get('name') == 'c_user'), None)
        
        if not c_user:
            print("⚠️ Cookies 異常，需要重新登入...")
            return False
        
        # 檢查是否即將過期（1天內）
        expires = c_user.get('expires', -1)
        now = time.time()
        
        if expires > 0 and expires - now < 86400:
            print(f"⚠️ 登入狀態即將過期，正在自動刷新...")
            return False
        
        return True
    except Exception as e:
        print(f"⚠️ 登入狀態檢查失敗: {e}")
        return False

# ==================== 主程序 ====================
def main():
    print("="*70)
    print("📘 Facebook 智能爬蟲 v5.0")
    print("="*70)
    print("技術方案：Playwright + 語義定位 + Cookie狀態保持\n")
    
    # 檢查登入狀態
    if not check_fb_login():
        print("\n" + "="*70)
        print("🔐 需要登入 Facebook")
        print("="*70)
        print("\n請選擇：")
        print("1. 運行 python3 fb_auto_login.py --setup 設置憑證（自動登入）")
        print("2. 運行 python3 fb_login.py 手動登入")
        print("3. 使用 28car 爬蟲（無需 FB 登入）")
        print("\n或直接回复你的 FB 電郵和密碼，我幫你設置：")
        print("   格式： fb 你的@email.com 你的密碼\n")
        return
    
    # 初始化
    conn, cursor = init_database()
    crawler = FacebookSmartCrawler()
    
    try:
        # 啟動瀏覽器
        crawler.start()
        
        total_saved = 0
        
        # 處理每個貼文
        for idx, post_url in enumerate(CONFIG['POST_URLS'], 1):
            print(f"\n📄 [{idx}/{len(CONFIG['POST_URLS'])}] 處理中...")
            
            # 提取留言
            comments = crawler.extract_comments_semantic(post_url)
            
            # 保存到數據庫
            saved = 0
            for comment in comments:
                if save_lead(cursor, conn, comment):
                    saved += 1
                    print(f"    ✅ {comment['commenter_name']}: {comment['comment_text'][:30]}...")
            
            total_saved += saved
            print(f"\n  📊 保存 {saved}/{len(comments)} 條留言")
            
            # 休息避免被限制
            if idx < len(CONFIG['POST_URLS']):
                import time
                time.sleep(5)
        
        # 導出Excel
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 爬蟲完成！")
        print("="*70)
        print(f"📊 本次新增: {total_saved} 條")
        print(f"📊 數據庫總計: {total_records} 條")
        print(f"📁 Excel導出: {CONFIG['EXCEL_PATH']}")
        
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
