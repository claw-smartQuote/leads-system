#!/usr/bin/env python3
"""
Facebook 留言爬蟲 - 優化版 v3.0
根據實際HTML結構優化選擇器
"""

import re
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

CONFIG = {
    'POST_URLS': [
        'https://www.facebook.com/Zhuhaiinsurance/posts/pfbid0XSTnRUi6A6Xtq4P1tUka2mAt3Vfuiq3VeyvpqDSE1HzzbQ6ChLWJD5dPWiEQURjql',
    ],
    'DB_PATH': Path.home() / '.fb_crawler' / 'fb_leads_v3.db',
    'EXCEL_PATH': Path.home() / '.fb_crawler' / 'fb_潛客名單_v3.xlsx',
    'STORAGE_STATE_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
}

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
    except:
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

class FacebookCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False, slow_mo=300)
        
        storage_state = str(CONFIG['STORAGE_STATE_PATH']) if CONFIG['STORAGE_STATE_PATH'].exists() else None
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.context.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
        self.page = self.context.new_page()
        
    def scroll_and_expand(self):
        """滾動並展開所有留言"""
        import time
        # 滾動
        for _ in range(5):
            self.page.evaluate('window.scrollBy(0, 800)')
            time.sleep(1.5)
        
        # 展開留言
        for _ in range(15):
            clicked = False
            try:
                buttons = self.page.locator('[role="button"]').all()
                for btn in buttons:
                    try:
                        text = btn.inner_text(timeout=500)
                        if any(k in text for k in ['查看更多', '則留言', 'View more']):
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
        """提取留言 - 優化版"""
        import time
        print(f"\n🌐 訪問: {post_url[:60]}...")
        
        self.page.goto(post_url, timeout=60000)
        time.sleep(5)
        
        print("  滾動並展開留言...")
        self.scroll_and_expand()
        
        print("  提取留言資料...")
        comments = []
        
        # 策略1: 直接找所有 <a> 標籤，篩選符合用戶檔案格式的
        all_links = self.page.locator('a').all()
        print(f"  頁面共有 {len(all_links)} 個連結")
        
        seen_urls = set()
        
        for link in all_links:
            try:
                href = link.get_attribute('href', timeout=100)
                if not href:
                    continue
                
                # 篩選用戶檔案連結
                # 格式1: https://www.facebook.com/username
                # 格式2: https://www.facebook.com/profile.php?id=xxx
                is_user = False
                clean_url = ""
                
                if '/profile.php?id=' in href:
                    # 提取ID
                    match = re.search(r'/profile\.php\?id=(\d+)', href)
                    if match:
                        clean_url = f"https://www.facebook.com/profile.php?id={match.group(1)}"
                        is_user = True
                elif re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)/?$', href.split('?')[0]):
                    username = href.split('?')[0].split('/')[-1]
                    # 排除常見非用戶路徑
                    if username and username not in ['login', 'recover', 'help', 'privacy', 'terms', 
                                                      'about', 'careers', 'watch', 'marketplace', 
                                                      'groups', 'pages', 'events']:
                        clean_url = f"https://www.facebook.com/{username}"
                        is_user = True
                
                if not is_user or not clean_url:
                    continue
                
                # 去重
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                
                # 獲取用戶名稱
                name = link.inner_text(timeout=200).strip()
                if not name or len(name) < 2 or len(name) > 50:
                    continue
                
                # 排除常見非用戶文字
                exclude_list = ['讚', '回覆', 'Reply', 'Like', '更多', '分享', 'Comment', 
                               '登入', '忘記帳戶', 'WhatsApp', 'Messenger', '分享給朋友']
                if name in exclude_list or any(e in name for e in exclude_list):
                    continue
                
                # 排除純數字或URL
                if name.replace('.', '').replace('/', '').isdigit() or name.startswith('http'):
                    continue
                
                # 嘗試提取留言內容
                comment_text = ""
                try:
                    # 找到該連結所在的整個留言容器
                    # 向上找多層父元素
                    for xpath_level in [1, 2, 3, 4, 5]:
                        try:
                            xpath = 'xpath=ancestor::div[' + str(xpath_level) + ']'
                            container = link.locator(xpath).first
                            if container.count() > 0:
                                # 在容器內找文字內容（排除用戶名）
                                text_divs = container.locator('div[dir="auto"]').all()
                                for div in text_divs:
                                    text = div.inner_text(timeout=200).strip()
                                    if text and text != name and len(text) > 2:
                                        if text not in exclude_list and not text.startswith('http'):
                                            comment_text = text
                                            break
                                if comment_text:
                                    break
                        except:
                            continue
                except:
                    pass
                
                comments.append({
                    'post_url': post_url,
                    'commenter_name': name,
                    'commenter_profile_url': clean_url,
                    'comment_text': comment_text[:500] if comment_text else "(無法提取)"
                })
                print(f"    ✅ {name}: {comment_text[:40] if comment_text else '(無內容)'}...")
                
            except Exception as e:
                continue
        
        return comments
    
    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

def main():
    print("="*70)
    print("📘 Facebook 留言爬蟲 - 優化版 v3.0")
    print("="*70)
    
    conn, cursor = init_database()
    crawler = FacebookCrawler()
    crawler.start()
    
    total_saved = 0
    
    try:
        for post_url in CONFIG['POST_URLS']:
            comments = crawler.extract_comments(post_url)
            
            saved = 0
            for comment in comments:
                if save_lead(cursor, conn, comment):
                    saved += 1
            
            total_saved += saved
            print(f"\n  📊 保存 {saved}/{len(comments)} 條留言")
            
            import time
            time.sleep(3)
        
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 爬蟲完成！")
        print("="*70)
        print(f"📊 本次新增: {total_saved} 條")
        print(f"📊 總計: {total_records} 條")
        print(f"📁 Excel: {CONFIG['EXCEL_PATH']}")
        
    finally:
        crawler.close()
        conn.close()

if __name__ == '__main__':
    main()
