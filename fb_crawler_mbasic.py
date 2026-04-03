#!/usr/bin/env python3
"""
Facebook mbasic 爬蟲 v1.0
使用 mbasic.facebook.com (輕量版 Facebook)
"""

import re
import sqlite3
import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==================== 設定 ====================
CONFIG = {
    'TARGET_PAGES': [
        'Zhuhaiinsurance',  # 珠海保險
    ],
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_mbasic.db'),
    'EXCEL_PATH': Path(f'/Users/claw/.openclaw/workspace/fb_潛客_mbasic_{datetime.now().strftime("%Y%m%d")}.xlsx'),
    'COOKIES_PATH': Path.home() / '.fb_crawler' / 'fb_storage_state.json',
}

# ==================== 初始化 ====================
def init_database():
    CONFIG['DB_PATH'].parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT,
            commenter_name TEXT,
            commenter_profile TEXT,
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
            (post_url, commenter_name, commenter_profile, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['post_url'], data[' commenter_name'], data['commenter_profile'],
            data['comment_text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"  ⚠️ 保存失敗: {e}")
        return False

def load_cookies():
    """載入 Facebook cookies"""
    if not CONFIG['COOKIES_PATH'].exists():
        print(f"❌ 找不到 cookies: {CONFIG['COOKIES_PATH']}")
        return None
    
    with open(CONFIG['COOKIES_PATH']) as f:
        state = json.load(f)
    
    cookies = {}
    for c in state.get('cookies', []):
        cookies[c['name']] = c['value']
    
    print(f"✅ 載入 {len(cookies)} 個 cookies")
    return cookies

def export_to_excel(cursor):
    cursor.execute('SELECT commenter_name, commenter_profile, comment_text, post_url, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者', '個人連結', '留言內容', '帖子連結', '抓取時間'])
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False)
    return len(df)

# ==================== mbasic 爬蟲 ====================
class MbasicCrawler:
    def __init__(self, cookies):
        self.cookies = cookies
        self.session = requests.Session()
        self.session.cookies.update(cookies)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-HK,zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def get_page(self, url, timeout=30):
        """發送請求並處理錯誤"""
        for attempt in range(3):
            try:
                r = self.session.get(url, timeout=timeout, allow_redirects=True)
                if r.status_code == 200:
                    return r.text
                elif r.status_code == 400:
                    print(f"  ⚠️ HTTP 400，可能需要刷新 cookies")
                    return None
                else:
                    print(f"  ⚠️ HTTP {r.status_code}")
            except Exception as e:
                print(f"  ⚠️ 請求失敗: {e}")
                time.sleep(5)
        return None
    
    def extract_posts(self, html):
        """從頁面提取帖子連結"""
        # mbasic 格式的帖子連結
        post_links = re.findall(r'href="(/[^"?]*?footprint[^"?]*?)"', html)
        # 也嘗試其他格式
        post_links += re.findall(r'href="(/story\.php\?story_fbid=[^"&]+)"', html)
        post_links += re.findall(r'href="(/[^/]+/posts/[^"?]+)"', html)
        
        # 清理並去重
        cleaned = []
        for link in set(post_links):
            if 'profile' not in link and 'group' not in link:
                full_url = 'https://mbasic.facebook.com' + link if link.startswith('/') else link
                cleaned.append(full_url)
        
        return cleaned
    
    def extract_comments(self, html, post_url):
        """從帖子頁面提取留言"""
        comments = []
        
        # 找留言者名稱和內容
        # mbasic 格式: <h3><a href="/user/xxx">名稱</a></h3><p>留言內容</p>
        
        # 方法1: 找用戶連結和相鄰的留言
        user_pattern = r'<h3[^>]*><a[^>]*href="(/[^"]+)"[^>]*>([^<]+)</a></h3>'
        content_pattern = r'</h3><p>([^<]+)</p>'
        
        users = re.findall(user_pattern, html)
        contents = re.findall(content_pattern, html)
        
        for i, (profile, name) in enumerate(users):
            if i < len(contents):
                comments.append({
                    'commenter_name': name.strip(),
                    'commenter_profile': 'https://mbasic.facebook.com' + profile,
                    'comment_text': contents[i].strip(),
                })
        
        # 方法2: 找展開更多的連結
        more_links = re.findall(r'href="(/page[^?"]+)"[^>]*>更多留言</a>', html)
        for link in more_links:
            more_url = 'https://mbasic.facebook.com' + link
            more_html = self.get_page(more_url)
            if more_html:
                more_comments = self.extract_comments_from_block(more_html, post_url)
                comments.extend(more_comments)
        
        return comments
    
    def extract_comments_from_block(self, html, post_url):
        """從留言區塊提取留言"""
        comments = []
        
        # 找所有用戶-內容配對
        blocks = re.findall(r'<h3[^>]*><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a></h3><p>([^<]+)</p>', html)
        
        for profile, name, content in blocks:
            comments.append({
                'commenter_name': name.strip(),
                'commenter_profile': 'https://mbasic.facebook.com' + profile,
                'comment_text': content.strip(),
            })
        
        return comments
    
    def scrape_page(self, page_name):
        """爬取指定粉絲頁"""
        print(f"\n📘 爬取: {page_name}")
        
        url = f'https://mbasic.facebook.com/{page_name}'
        html = self.get_page(url)
        
        if not html:
            print(f"  ❌ 無法獲取頁面")
            return []
        
        # 檢查是否需要登入
        if 'login' in html.lower() or '登入' in html:
            print(f"  ❌ 需要登入")
            return []
        
        posts = self.extract_posts(html)
        print(f"  找到 {len(posts)} 個帖子")
        
        all_comments = []
        for i, post_url in enumerate(posts[:5]):  # 限制每頁5個帖子
            print(f"  [{i+1}/{min(5, len(posts))}] 處理: {post_url[:50]}...")
            post_html = self.get_page(post_url)
            
            if post_html:
                comments = self.extract_comments(post_html, post_url)
                print(f"      找到 {len(comments)} 條留言")
                all_comments.extend(comments)
            
            time.sleep(2)  # 礼貌延迟
        
        return all_comments

# ==================== 主程式 ====================
def main():
    print("=" * 50)
    print("📘 Facebook mbasic 爬蟲 v1.0")
    print("=" * 50)
    
    # 載入 cookies
    cookies = load_cookies()
    if not cookies:
        print("❌ 無法繼續，請先登入 Facebook")
        return
    
    # 初始化數據庫
    conn, cursor = init_database()
    
    # 創建爬蟲
    crawler = MbasicCrawler(cookies)
    
    # 爬取每個頁面
    total_comments = 0
    for page in CONFIG['TARGET_PAGES']:
        comments = crawler.scrape_page(page)
        
        for comment in comments:
            if save_lead(cursor, conn, {**comment, 'post_url': ''}):
                total_comments += 1
        
        time.sleep(3)
    
    print(f"\n✅ 共抓取 {total_comments} 條新留言")
    
    # 匯出
    if total_comments > 0:
        count = export_to_excel(cursor)
        print(f"✅ 已匯出 {count} 筆記錄")
    
    conn.close()
    print("\n👋 完成!")

if __name__ == '__main__':
    main()
