#!/usr/bin/env python3
"""
Facebook 留言爬蟲 - 智能語義定位版 v5.2
基於 2026-04-03 實際操作學習的改進

改進點：
1. Facebook 群組帖子以對話框形式打開
2. 需要點擊「查看 X 則回覆」按鈕展開回覆
3. 對話框內滾動使用 ArrowDown 鍵
4. 動態加載內容需要等待
5. 留言在 [role="article"] 區塊內
"""

import re
import sqlite3
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ==================== 設定 ====================
CONFIG = {
    'POST_URLS': [
        'https://www.facebook.com/share/p/1DrEnCiSTY/',
    ],
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_final.db'),
    'EXCEL_PATH': Path(f'/Users/claw/.openclaw/workspace/fb_潛客_{datetime.now().strftime("%Y%m%d")}.xlsx'),
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

# ==================== Facebook 智能爬蟲 v5.2 ====================
class FacebookSmartCrawler:
    """
    基於實際操作學習的改進版爬蟲
    
    關鍵發現：
    1. Facebook 群組帖子打開時是 [role="dialog"] 覆蓋層
    2. 留言內容在 dialog 內的 [role="article"] 元素
    3. 需要展開 "查看 X 則回覆" 按鈕
    4. 滾動要對 dialog 元素操作，不能用 window.scroll
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self, headless=False):
        """啟動瀏覽器並加載登入狀態"""
        playwright = sync_playwright().start()
        
        self.browser = playwright.chromium.launch(
            headless=headless,
            slow_mo=300,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
            ]
        )
        
        storage_state = None
        if CONFIG['STORAGE_STATE_PATH'].exists():
            print(f"🔑 加載登入狀態: {CONFIG['STORAGE_STATE_PATH']}")
            storage_state = str(CONFIG['STORAGE_STATE_PATH'])
        
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
        self.page.set_default_timeout(60000)
        
    def _is_valid_user(self, href, name):
        """檢查是否為有效用戶"""
        if not href or not name:
            return False
        if len(name) < 2 or len(name) > 50:
            return False
        # 過濾非用戶名
        forbidden_names = ['讚', '回覆', 'Like', 'Reply', '更多', '分享', 'Comment', '登入', '留言', '回應', 'Messenger', '通知']
        if name in forbidden_names:
            return False
        # 過濾非個人檔案連結
        if any(x in href for x in ['/login', '/recover', '/help/', '/privacy', '/l.php', 'l.facebook']):
            return False
        return True
    
    def _clean_profile_url(self, href):
        """清理用戶URL為個人檔案格式"""
        if not href:
            return None
        
        # 處理 /groups/xxx/user/xxx 格式（群組成員）
        groups_match = re.search(r'/groups/\d+/user/(\d+)', href)
        if groups_match:
            return f"https://www.facebook.com/profile.php?id={groups_match.group(1)}"
        
        # 處理 /profile.php?id=xxx 格式
        if '/profile.php?id=' in href:
            match = re.search(r'id=(\d+)', href)
            if match:
                return f"https://www.facebook.com/profile.php?id={match.group(1)}"
        
        # 處理 /username 格式
        match = re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)', href)
        if match:
            username = match.group(1)
            forbidden = ['login', 'recover', 'help', 'privacy', 'watch', 'marketplace', 
                        'groups', 'search', 'settings', 'friends', 'photos', 'games']
            if username.lower() not in forbidden:
                return f"https://www.facebook.com/{username}"
        
        return None
    
    def _extract_comment_text(self, article, exclude_name):
        """從留言區塊提取文字內容"""
        try:
            # 找所有 dir="auto" 的元素（Facebook 留言通常用這個）
            text_elements = article.locator('div[dir="auto"]').all()
            
            for elem in text_elements:
                try:
                    text = elem.inner_text(timeout=300).strip()
                    # 排除用戶名和按鈕文字
                    if text and len(text) > 3:
                        if text not in [exclude_name, '讚', '回覆', '分享', '更多', '編輯', '刪除']:
                            # 排除時間文字
                            if not any(x in text.lower() for x in ['小時前', '分鐘前', '天前', '星期前', '月前', '年前']):
                                return text[:500]
                except:
                    pass
        except:
            pass
        
        return "(無法提取)"
    
    def expand_replies_in_dialog(self):
        """
        在對話框內展開所有回覆
        基於實際操作：點擊 "查看 X 則回覆" 按鈕
        """
        print("    💬 展開回覆...")
        
        expanded_total = 0
        
        # 持續點擊直到沒有更多
        for _ in range(30):
            clicked = 0
            
            # 方法1: 找包含數字的 "則回覆" 按鈕
            try:
                # 找所有包含 "查看" 和數字的按鈕
                all_buttons = self.page.locator('[role="button"]').all()
                
                for btn in all_buttons:
                    try:
                        text = btn.inner_text(timeout=500) or ''
                        # 匹配 "查看 X 則回覆" 或 "View X replies"
                        if re.search(r'查看\s*\d+\s*則回覆', text) or \
                           re.search(r'View\s*\d+\s*repl', text, re.IGNORECASE):
                            if btn.is_visible() and btn.is_enabled():
                                btn.click(timeout=1000)
                                clicked += 1
                                time.sleep(0.5)
                    except:
                        pass
            except Exception as e:
                pass
            
            if clicked > 0:
                expanded_total += clicked
                print(f"      已展開 {expanded_total} 個回覆按鈕")
            
            # 如果一次都沒點到，嘗試滾動對話框
            if clicked == 0:
                # 嘗試按 ArrowDown 鍵
                try:
                    dialog = self.page.locator('[role="dialog"]').first
                    if dialog.count() > 0:
                        # 聚焦並滾動
                        for _ in range(3):
                            self.page.keyboard.press('ArrowDown')
                            time.sleep(0.3)
                except:
                    pass
                time.sleep(0.5)
            
            # 如果連續2次都沒有可點的，停止
            if clicked == 0 and expanded_total > 0:
                # 最後檢查一次
                time.sleep(1)
                continue
            elif clicked == 0 and expanded_total == 0:
                # 一開始就沒有，嘗試幾次後放棄
                break
        
        print(f"    ✅ 回覆展開完成 (共 {expanded_total} 個)")
        return expanded_total
    
    def scroll_dialog_to_bottom(self, max_scrolls=20):
        """
        滾動對話框到底部以加載所有留言
        使用 ArrowDown 鍵滾動
        """
        print("    📜 滾動加載留言...")
        
        last_count = 0
        
        for i in range(max_scrolls):
            # 按多次 ArrowDown
            for _ in range(5):
                self.page.keyboard.press('ArrowDown')
                time.sleep(0.2)
            
            # 等待新內容
            time.sleep(1)
            
            # 檢查當前留言數
            try:
                articles = self.page.locator('[role="article"]').all()
                current_count = len(articles)
                
                if current_count > last_count:
                    print(f"      滾動 {i+1}: 找到 {current_count} 個留言")
                    last_count = current_count
                
                # 如果連續2次數量不變，可能到底了
                if i > 5 and current_count == last_count:
                    print(f"      已到達底部，共 {current_count} 個留言")
                    break
                    
            except Exception as e:
                pass
        
        return last_count
    
    def extract_comments_from_dialog(self, post_url):
        """
        從對話框提取所有留言
        核心邏輯：找到 [role="article"] 元素
        """
        print("    📥 提取留言...")
        
        comments = []
        seen_profiles = set()
        
        try:
            # 找到對話框
            dialog = self.page.locator('[role="dialog"]').first
            
            # 在對話框內找所有 article（留言區塊）
            articles = dialog.locator('[role="article"]').all()
            print(f"      找到 {len(articles)} 個留言區塊")
            
            for idx, article in enumerate(articles):
                try:
                    # 找用戶連結（在群組內是 /groups/xxx/user/xxx 格式）
                    user_links = article.locator('a[href*="/groups/"]').all()
                    
                    if not user_links:
                        # 嘗試其他格式
                        user_links = article.locator('a[href*="facebook.com"]').all()
                    
                    for user_link in user_links:
                        try:
                            href = user_link.get_attribute('href', timeout=500) or ''
                            name = user_link.inner_text(timeout=500).strip()
                            
                            if not self._is_valid_user(href, name):
                                continue
                            
                            clean_url = self._clean_profile_url(href)
                            if not clean_url or clean_url in seen_profiles:
                                continue
                            seen_profiles.add(clean_url)
                            
                            # 提取留言內容
                            comment_text = self._extract_comment_text(article, name)
                            
                            comments.append({
                                'post_url': post_url,
                                'commenter_name': name,
                                'commenter_profile_url': clean_url,
                                'comment_text': comment_text
                            })
                            
                            print(f"        ✅ {name}: {comment_text[:30]}...")
                            break  # 只取第一個有效用戶
                            
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ⚠️ 提取失敗: {e}")
        
        return comments
    
    def scrape_post(self, post_url):
        """
        爬取單個帖子的完整流程
        """
        print(f"\n🌐 訪問帖子: {post_url[:50]}...")
        
        # 1. 訪問頁面
        self.page.goto(post_url, wait_until='domcontentloaded', timeout=90000)
        time.sleep(3)
        
        # 2. 如果有彈窗，嘗試關閉並直接訪問
        try:
            close_btn = self.page.locator('[aria-label="關閉"]').first
            if close_btn.is_visible():
                close_btn.click()
                time.sleep(1)
                print("    已關閉彈窗")
        except:
            pass
        
        # 3. 展開所有回覆
        self.expand_replies_in_dialog()
        
        # 4. 滾動加載所有留言
        self.scroll_dialog_to_bottom()
        
        # 5. 提取留言
        comments = self.extract_comments_from_dialog(post_url)
        
        return comments
    
    def close(self):
        """關閉瀏覽器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

# ==================== 登入檢查 ====================
def check_fb_login():
    """檢查 FB 登入狀態"""
    storage_path = Path.home() / '.fb_crawler' / 'fb_storage_state.json'
    
    if not storage_path.exists():
        print("⚠️ 未找到 FB 登入狀態")
        return False
    
    try:
        with open(storage_path, 'r') as f:
            state = json.load(f)
        
        cookies = state.get('cookies', [])
        c_user = next((c for c in cookies if c.get('name') == 'c_user'), None)
        
        if not c_user:
            print("⚠️ Cookies 異常（缺少 c_user）")
            return False
        
        return True
    except Exception as e:
        print(f"⚠️ 登入狀態檢查失敗: {e}")
        return False

# ==================== 主程序 ====================
def main():
    print("="*70)
    print("📘 Facebook 智能爬蟲 v5.2")
    print("="*70)
    print("改進：對話框內滾動 + 回覆自動展開\n")
    
    # 檢查登入狀態
    if not check_fb_login():
        print("\n" + "="*70)
        print("🔐 需要登入 Facebook")
        print("="*70)
        print("\n請選擇：")
        print("1. 運行 python3 fb_auto_login.py --setup 設置憑證（自動登入）")
        print("2. 運行 python3 fb_login.py 手動登入")
        print("3. 使用 28car 爬蟲（無需 FB 登入）")
        return
    
    # 初始化
    conn, cursor = init_database()
    crawler = FacebookSmartCrawler()
    
    try:
        # 啟動瀏覽器
        print("🚀 啟動瀏覽器...")
        crawler.start(headless=False)  # 建議用非無頭模式
        
        total_saved = 0
        
        for idx, post_url in enumerate(CONFIG['POST_URLS'], 1):
            print(f"\n📄 [{idx}/{len(CONFIG['POST_URLS'])}] 處理中...")
            
            # 爬取
            comments = crawler.scrape_post(post_url)
            
            # 保存
            saved = 0
            for comment in comments:
                if save_lead(cursor, conn, comment):
                    saved += 1
            
            total_saved += saved
            print(f"\n  📊 保存 {saved}/{len(comments)} 條留言")
            
            if idx < len(CONFIG['POST_URLS']):
                time.sleep(5)
        
        # 導出
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
        print("\n👋 完成")

if __name__ == '__main__':
    main()
