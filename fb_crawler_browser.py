#!/usr/bin/env python3
"""
Facebook 瀏覽器爬蟲 v1.0
使用 OpenClaw Browser CDP 自動化
"""

import json
import sqlite3
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==================== 設定 ====================
CONFIG = {
    'TARGET_POSTS': [
        'https://www.facebook.com/share/p/1DrEnCiSTY/',
    ],
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_browser.db'),
    'EXCEL_PATH': Path(f'/Users/claw/.openclaw/workspace/fb_潛客_browser_{datetime.now().strftime("%Y%m%d")}.xlsx'),
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
            data['post_url'], data['commenter_name'], data['commenter_profile'],
            data['comment_text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"  ⚠️ 保存失敗: {e}")
        return False

def export_to_excel(cursor):
    cursor.execute('SELECT commenter_name, commenter_profile, comment_text, post_url, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者', '個人連結', '留言內容', '帖子連結', '抓取時間'])
    CONFIG['EXCEL_PATH'].parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(CONFIG['EXCEL_PATH'], index=False)
    return len(df)

# ==================== 瀏覽器爬蟲 ====================
def browser_action(action, params=None):
    """通過 OpenClaw gateway 發送瀏覽器指令"""
    import urllib.request
    import urllib.parse
    
    # CDP 命令
    if action == 'goto':
        # Navigate to URL
        return {'url': params['url']}
    elif action == 'snapshot':
        return {'get': 'snapshot'}
    elif action == 'click':
        return {'click': params['ref']}
    elif action == 'wait':
        return {'wait': params['ms']}
    return None

def get_browser_tabs():
    """獲取瀏覽器 Tab 列表"""
    import subprocess
    result = subprocess.run(
        ['openclaw', 'browser', 'tabs', '--json'],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except:
        return []

def extract_comments_from_snapshot(snapshot_text):
    """從 snapshot 文本提取留言"""
    import re
    
    comments = []
    
    # 找所有留言區塊 - 通常包含 "的回應" 或 comment 相關元素
    # 格式: [ref=xxx] link "用户名" 或 heading "用户名"
    
    # 匹配留言者名稱和內容
    patterns = [
        # 留言者名稱模式
        r'link "([^"]+)" \[ref=e\d+\] \[cursor=pointer\]:\s*\n\s*/url: /groups/\d+/user/\d+',
        # 回應區塊
        r'article "([^"]+) 的回應',
        # 用戶連結
        r'link "([^"]+)":\s*\n\s*/url: /groups/\d+/user/',
    ]
    
    names = set()
    for pattern in patterns:
        matches = re.findall(pattern, snapshot_text)
        for m in matches:
            if len(m) > 1 and len(m) < 50:  # 過濾太短或太長的
                names.add(m)
    
    # 找留言內容 - 通常在留言者名稱後面的段落
    content_pattern = r'generic "([^"]+)":\s*\n\s*generic:\s*\n\s*generic:\s*\n\s*generic:\s*\n\s*generic:\s*\n\s*link'
    contents = re.findall(content_pattern, snapshot_text)
    
    # 組合
    for name in names:
        # 找這個用戶的留言內容
        for i, content in enumerate(contents):
            if len(content) > 5 and len(content) < 500:
                comments.append({
                    'commenter_name': name,
                    'commenter_profile': '',
                    'comment_text': content
                })
    
    return comments[:50]  # 限制數量

def scrape_with_browser(post_url):
    """使用瀏覽器自動化爬取帖子"""
    import subprocess
    import json
    
    print(f"  🌐 訪問: {post_url[:60]}...")
    
    # 1. 開啟新 Tab
    subprocess.run(['openclaw', 'browser', 'open', '--new-tab', post_url], 
                   capture_output=True)
    time.sleep(5)  # 等待頁面加載
    
    # 2. 滾動頁面加載更多內容
    for _ in range(3):
        subprocess.run(['openclaw', 'browser', 'act', '--scroll', 'down'],
                       capture_output=True)
        time.sleep(2)
    
    # 3. 截圖/獲取 snapshot
    result = subprocess.run(['openclaw', 'browser', 'snapshot', '--json'],
                           capture_output=True, text=True)
    
    try:
        snapshot = json.loads(result.stdout)
        comments = extract_comments_from_snapshot(str(snapshot))
        return comments
    except Exception as e:
        print(f"  ⚠️ 解析失敗: {e}")
        return []

# ==================== 主程式 ====================
def main():
    print("=" * 50)
    print("📘 Facebook 瀏覽器爬蟲 v1.0")
    print("=" * 50)
    
    # 初始化數據庫
    conn, cursor = init_database()
    
    total_comments = 0
    for post_url in CONFIG['TARGET_POSTS']:
        print(f"\n📄 處理帖子...")
        
        comments = scrape_with_browser(post_url)
        print(f"  找到 {len(comments)} 條留言")
        
        for comment in comments:
            data = {**comment, 'post_url': post_url}
            if save_lead(cursor, conn, data):
                total_comments += 1
    
    print(f"\n✅ 共抓取 {total_comments} 條新留言")
    
    if total_comments > 0:
        count = export_to_excel(cursor)
        print(f"✅ 已匯出 {count} 筆記錄")
    
    conn.close()
    print("\n👋 完成!")

if __name__ == '__main__':
    main()
