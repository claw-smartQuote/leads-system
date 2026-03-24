#!/usr/bin/env python3
"""
Facebook 粉絲專頁爬蟲 - v8.0
自動提取專頁所有貼文及留言
"""

import re
import time
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

CONFIG = {
    # 目標粉絲專頁
    'PAGE_URL': 'https://www.facebook.com/Zhuhaiinsurance',  # 可修改為其他專頁
    'MAX_POSTS': 15,  # 最多處理的貼文數
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_page_leads.db'),
    'EXCEL_PATH': Path('/Users/claw/.openclaw/workspace/fb_專頁潛客.xlsx'),
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
            post_content TEXT,
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
            (post_url, post_content, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['post_url'], data.get('post_content', ''),
            data['commenter_name'], data['commenter_profile_url'],
            data['comment_text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"  ⚠️ 保存失敗: {e}")
        return False

def export_to_excel(cursor):
    cursor.execute('''
        SELECT commenter_name, commenter_profile_url, comment_text, post_content, post_url, scraped_at 
        FROM fb_leads ORDER BY scraped_at DESC
    ''')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文內容', '貼文連結', '抓取時間'])
    df.to_excel(CONFIG['EXCEL_PATH'], index=False, engine='openpyxl')
    return len(df)

class FacebookPageCrawler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(
            headless=False,
            slow_mo=800,
            args=['--disable-blink-features=AutomationControlled']
        )
        storage_state = str(CONFIG['STORAGE_STATE_PATH']) if CONFIG['STORAGE_STATE_PATH'].exists() else None
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
        
    def get_page_posts(self):
        """從粉絲專頁提取貼文連結"""
        print(f"\n🌐 訪問專頁: {CONFIG['PAGE_URL']}")
        
        self.page.goto(CONFIG['PAGE_URL'], wait_until='networkidle', timeout=90000)
        time.sleep(5)
        
        print("  滾動加載貼文...")
        # 多次滾動加載更多貼文
        for i in range(15):
            self.page.evaluate('window.scrollBy(0, 1000)')
            time.sleep(2)
            if i % 3 == 0:
                print(f"    已滾動 {i+1} 次...")
        
        # 提取貼文連結 - 多種策略
        post_urls = []
        seen = set()
        
        print("\n  提取貼文連結...")
        
        # 策略1: 找所有包含 /posts/ 的連結
        all_links = self.page.locator('a').all()
        print(f"    頁面共有 {len(all_links)} 個連結")
        
        for link in all_links:
            try:
                href = link.get_attribute('href', timeout=100) or ''
                
                # 篩選貼文連結 (多種格式)
                is_post = False
                clean_url = ""
                
                if '/posts/' in href:
                    # 格式: /username/posts/123456
                    clean_url = href.split('?')[0].split('&')[0]
                    is_post = True
                elif 'pfbid' in href:
                    # 格式: /username/posts/pfbidxxxxx
                    clean_url = href.split('?')[0].split('&')[0]
                    is_post = True
                
                if is_post and clean_url and clean_url not in seen:
                    # 確保是當前專頁的貼文
                    if CONFIG['PAGE_URL'].split('/')[-1] in clean_url or 'facebook.com' in clean_url:
                        post_urls.append(clean_url)
                        seen.add(clean_url)
                        
                if len(post_urls) >= CONFIG['MAX_POSTS']:
                    break
                    
            except:
                pass
        
        print(f"  ✅ 提取 {len(post_urls)} 個貼文連結")
        
        # 顯示找到的貼文
        if post_urls:
            print("\n  📋 找到的貼文:")
            for i, url in enumerate(post_urls[:5], 1):
                print(f"    {i}. {url[:70]}...")
            if len(post_urls) > 5:
                print(f"    ... 還有 {len(post_urls) - 5} 個")
        
        return post_urls
    
    def extract_post_and_comments(self, post_url):
        """提取單個貼文的內容和留言"""
        print(f"\n  📄 處理: {post_url[:50]}...")
        
        try:
            self.page.goto(post_url, wait_until='networkidle', timeout=90000)
            time.sleep(5)
            
            # 滾動
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
                        if any(k in text for k in ['更多', 'more', '則', 'view']):
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
            
            # 提取貼文內容
            post_content = ""
            try:
                content_divs = self.page.locator('div[dir="auto"]').all()
                for div in content_divs[:5]:
                    text = div.inner_text(timeout=500).strip()
                    if len(text) > 20:
                        post_content = text[:200]
                        break
            except:
                pass
            
            # 提取留言
            comments = []
            seen = set()
            
            # 使用 article 策略
            articles = self.page.locator('[role="article"]').all()
            
            for article in articles:
                try:
                    user_link = article.locator('a[href*="facebook.com"]').first
                    if user_link.count() == 0:
                        continue
                    
                    href = user_link.get_attribute('href', timeout=500) or ''
                    name = user_link.inner_text(timeout=500).strip()
                    
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
                            if username not in ['login', 'recover', 'help']:
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
                        'post_url': post_url,
                        'post_content': post_content,
                        'commenter_name': name,
                        'commenter_profile_url': clean_url,
                        'comment_text': comment_text[:500] if comment_text else "(無法提取)"
                    })
                    
                except:
                    pass
            
            return comments
            
        except Exception as e:
            print(f"    ❌ 錯誤: {e}")
            return []
    
    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

def main():
    print("="*70)
    print("📘 Facebook 粉絲專頁爬蟲 v8.0")
    print("="*70)
    print(f"目標專頁: {CONFIG['PAGE_URL']}")
    print(f"最多處理: {CONFIG['MAX_POSTS']} 個貼文\n")
    
    conn, cursor = init_database()
    crawler = FacebookPageCrawler()
    
    try:
        crawler.start()
        
        # 獲取專頁中的貼文連結
        post_urls = crawler.get_page_posts()
        
        if not post_urls:
            print("\n⚠️ 未找到任何貼文")
            print("提示: Facebook專頁結構複雜，可能需要手動提供貼文URL")
            return
        
        # 處理每個貼文
        total_comments = 0
        
        for idx, post_url in enumerate(post_urls, 1):
            print(f"\n[{idx}/{len(post_urls)}] 處理貼文...")
            
            comments = crawler.extract_post_and_comments(post_url)
            
            saved = 0
            for comment in comments:
                if save_lead(cursor, conn, comment):
                    saved += 1
                    print(f"    ✅ {comment['commenter_name']}: {comment['comment_text'][:30]}...")
            
            total_comments += saved
            print(f"  📊 保存 {saved}/{len(comments)} 條留言")
            
            time.sleep(3)
        
        # 導出Excel
        total_records = export_to_excel(cursor)
        
        print("\n" + "="*70)
        print("✅ 專頁爬蟲完成！")
        print("="*70)
        print(f"📊 處理貼文: {len(post_urls)} 個")
        print(f"📊 新增留言: {total_comments} 條")
        print(f"📊 總計: {total_records} 條")
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
