#!/usr/bin/env python3
"""
Facebook 單一貼文爬蟲 - 直接指定URL
"""

import re
import time
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# 設定 - 直接指定貼文URL
POST_URL = 'https://www.facebook.com/Zhuhaiinsurance/posts/pfbid0257WFhkLDQuK2WZEhHVsYCW9xZYJUQWxRKw3uJiH2X7Thj9SQp4E3w6CnLRcB5bWjl'

DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_single_post.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/fb_單一貼文結果.xlsx')
STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'

def init_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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

print('='*60)
print('📝 Facebook 單一貼文爬蟲')
print('='*60)
print(f'目標貼文: {POST_URL}')
print()

conn, cursor = init_database()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=800)
    
    storage_state = str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH.exists() else None
    context = browser.new_context(
        storage_state=storage_state,
        viewport={'width': 1400, 'height': 900},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        locale='zh-HK',
    )
    
    context.add_init_script('''
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
    ''')
    
    page = context.new_page()
    page.set_default_timeout(60000)
    
    print('🌐 訪問貼文...')
    page.goto(POST_URL, wait_until='networkidle', timeout=90000)
    time.sleep(5)
    
    # 滾動
    print('  滾動加載...')
    for _ in range(8):
        page.evaluate('window.scrollBy(0, 800)')
        time.sleep(1.5)
    
    # 展開留言
    print('  展開留言...')
    for _ in range(15):
        try:
            buttons = page.locator('[role="button"]').all()
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
        page.evaluate('window.scrollBy(0, 800)')
        time.sleep(1.5)
    
    print('  提取留言...')
    
    # 提取留言 - 使用v5.0成功策略
    comments = []
    seen = set()
    
    # 策略1: role="article"
    articles = page.locator('[role="article"]').all()
    print(f'    找到 {len(articles)} 個 article 區塊')
    
    for article in articles:
        try:
            user_link = article.locator('a[href*="facebook.com"]').first
            if user_link.count() == 0:
                continue
            
            href = user_link.get_attribute('href', timeout=500) or ''
            name = user_link.inner_text(timeout=500).strip()
            
            if not name or len(name) < 2 or len(name) > 40:
                continue
            if name in ['讚', '回覆', 'Like', 'Reply', '更多', '分享']:
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
                        if text not in ['讚', '回覆', 'Like', 'Reply', '更多']:
                            comment_text = text
                            break
            except:
                pass
            
            comments.append({
                'post_url': POST_URL,
                'commenter_name': name,
                'commenter_profile_url': clean_url,
                'comment_text': comment_text[:500] if comment_text else "(無法提取)"
            })
            print(f"    ✅ {name}: {comment_text[:30] if comment_text else '(無內容)'}...")
            
        except:
            pass
    
    # 保存到數據庫
    saved = 0
    for comment in comments:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO fb_leads 
                (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                comment['post_url'], comment['commenter_name'], 
                comment['commenter_profile_url'], comment['comment_text'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            if cursor.rowcount > 0:
                saved += 1
        except:
            pass
    
    conn.commit()
    
    # 導出Excel
    cursor.execute('SELECT commenter_name, commenter_profile_url, comment_text, post_url, scraped_at FROM fb_leads')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    df.to_excel(EXCEL_PATH, index=False, engine='openpyxl')
    
    print(f'\n{"="*60}')
    print(f'✅ 完成！')
    print(f'📊 找到 {len(comments)} 條留言')
    print(f'📊 保存 {saved} 條新記錄')
    print(f'📊 總計: {len(rows)} 條')
    print(f'📁 Excel: {EXCEL_PATH}')
    
    input('\n按 Enter 結束...')
    browser.close()

conn.close()
print('\n👋 瀏覽器已關閉')
