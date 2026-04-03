#!/usr/bin/env python3
"""
Facebook 留言爬蟲 - 簡化有效版 v4.0
根據實際測試結果優化
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
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_v4.db'),
    'EXCEL_PATH': Path('/Users/claw/.openclaw/workspace/fb_潛客名單_v4.xlsx'),
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
    cursor.execute('SELECT commenter_name, commenter_profile_url, comment_text, post_url, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

class FacebookCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False, slow_mo=500)
        storage_state = str(CONFIG['STORAGE_STATE_PATH']) if CONFIG['STORAGE_STATE_PATH'].exists() else None
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900}
        )
        self.page = self.context.new_page()
        
    def extract_comments(self, post_url):
        import time
        print(f"\n🌐 訪問: {post_url[:50]}...")
        
        self.page.goto(post_url, timeout=90000)
        time.sleep(8)  # 等待內容加載
        
        # 多次滾動確保所有內容加載
        print("  滾動加載...")
        for _ in range(8):
            self.page.evaluate('window.scrollBy(0, 1000)')
            time.sleep(2)
        
        # 點擊展開更多留言
        print("  展開留言...")
        for _ in range(20):
            try:
                buttons = self.page.locator('text=/查看更多|View more|則留言/i').all()
                if buttons:
                    buttons[0].click()
                    time.sleep(2)
                else:
                    break
            except:
                break
        
        print("  提取資料...")
        comments = []
        seen = set()
        
        # 獲取頁面所有連結
        links = self.page.locator('a').all()
        
        for link in links:
            try:
                href = link.get_attribute('href', timeout=200) or ''
                text = link.inner_text(timeout=300).strip()
                
                # 篩選條件
                if not href or not text:
                    continue
                if len(text) < 2 or len(text) > 40:
                    continue
                if text in ['讚', '回覆', 'Like', 'Reply', '更多', '分享', 'Comment', '登入']:
                    continue
                
                # 識別用戶連結
                clean_url = ""
                if '/profile.php?id=' in href:
                    match = re.search(r'id=(\d+)', href)
                    if match:
                        clean_url = f"https://www.facebook.com/profile.php?id={match.group(1)}"
                elif 'facebook.com/' in href:
                    # 提取用戶名
                    parts = href.split('?')[0].split('/')
                    if len(parts) >= 4:
                        username = parts[-1] or parts[-2]
                        if username and username not in ['login', 'recover', 'help', 'watch', 'marketplace']:
                            clean_url = f"https://www.facebook.com/{username}"
                
                if not clean_url or clean_url in seen:
                    continue
                    
                # 驗證是否為個人檔案（排除頁面連結）
                if any(x in clean_url for x in ['/groups/', '/pages/', '/events/']):
                    continue
                
                seen.add(clean_url)
                
                comments.append({
                    'post_url': post_url,
                    'commenter_name': text,
                    'commenter_profile_url': clean_url,
                    'comment_text': ''
                })
                print(f"    ✅ {text}")
                
            except:
                pass
        
        return comments
    
    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

def main():
    print("="*60)
    print("📘 Facebook 留言爬蟲 - 簡化版 v4.0")
    print("="*60)
    
    conn, cursor = init_database()
    crawler = FacebookCrawler()
    crawler.start()
    
    total = 0
    try:
        for url in CONFIG['POST_URLS']:
            comments = crawler.extract_comments(url)
            
            saved = 0
            for c in comments:
                if save_lead(cursor, conn, c):
                    saved += 1
            
            total += saved
            print(f"\n  📊 保存 {saved}/{len(comments)} 條")
            time.sleep(3)
        
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*60)
        print("✅ 完成!")
        print("="*60)
        print(f"📊 本次: {total} 條")
        print(f"📊 總計: {total_records} 條")
        print(f"📁 Excel: {CONFIG['EXCEL_PATH']}")
        
    finally:
        crawler.close()
        conn.close()

if __name__ == '__main__':
    import time
    main()
