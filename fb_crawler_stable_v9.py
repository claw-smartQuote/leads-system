#!/usr/bin/env python3
"""
Facebook 貼文爬蟲 - 穩定版 v9.0
加入完整錯誤處理和重試機制
"""

import re
import time
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

# 設定
POST_URLS = [
    'https://www.facebook.com/Zhuhaiinsurance/posts/pfbid0257WFhkLDQuK2WZEhHVsYCW9xZYJUQWxRKw3uJiH2X7Thj9SQp4E3w6CnLRcB5bWjl',
]

DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_stable.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/fb_穩定版結果.xlsx')
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

def safe_scroll(page, amount=800):
    """安全滾動"""
    try:
        page.evaluate(f'window.scrollBy(0, {amount})')
        return True
    except:
        return False

def extract_comments_from_page(page, post_url):
    """從當前頁面提取留言"""
    comments = []
    seen = set()
    
    try:
        # 找所有 article 區塊
        articles = page.locator('[role="article"]').all()
        
        for article in articles:
            try:
                # 找用戶連結
                links = article.locator('a').all()
                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=200) or ''
                        name = link.inner_text(timeout=200).strip()
                        
                        # 篩選條件
                        if not name or len(name) < 2 or len(name) > 40:
                            continue
                        if name in ['讚', '回覆', 'Like', 'Reply', '更多', '分享']:
                            continue
                        
                        # 驗證是個人檔案連結
                        clean_url = None
                        if '/profile.php?id=' in href:
                            match = re.search(r'id=(\d+)', href)
                            if match:
                                clean_url = f"https://www.facebook.com/profile.php?id={match.group(1)}"
                        elif re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)/?\??', href):
                            username = re.match(r'https://www\.facebook\.com/([a-zA-Z0-9._-]+)', href).group(1)
                            if username not in ['login', 'recover', 'help', 'watch', 'marketplace']:
                                clean_url = f"https://www.facebook.com/{username}"
                        
                        if not clean_url or clean_url in seen:
                            continue
                        seen.add(clean_url)
                        
                        # 嘗試找留言內容
                        comment_text = ""
                        try:
                            # 在同個article內找其他文字
                            all_texts = article.locator('div[dir="auto"]').all()
                            for txt_div in all_texts:
                                txt = txt_div.inner_text(timeout=200).strip()
                                if txt and txt != name and len(txt) > 2:
                                    if txt not in ['讚', '回覆', 'Like', 'Reply']:
                                        comment_text = txt
                                        break
                        except:
                            pass
                        
                        comments.append({
                            'post_url': post_url,
                            'commenter_name': name,
                            'commenter_profile_url': clean_url,
                            'comment_text': comment_text[:500] if comment_text else ""
                        })
                        
                    except:
                        continue
                        
            except:
                continue
                
    except Exception as e:
        print(f"    提取錯誤: {e}")
    
    return comments

def main():
    print("="*60)
    print("📘 Facebook 爬蟲 - 穩定版 v9.0")
    print("="*60)
    
    conn, cursor = init_database()
    
    total_comments = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=1000,  # 更慢的動作
            args=['--disable-blink-features=AutomationControlled']
        )
        
        storage_state = str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH.exists() else None
        context = browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        )
        
        page = context.new_page()
        
        for post_url in POST_URLS:
            print(f"\n🌐 處理: {post_url[:50]}...")
            
            try:
                # 訪問頁面
                page.goto(post_url, timeout=90000)
                print("  頁面加載中...")
                time.sleep(8)  # 等待更長時間
                
                # 檢查是否需要登入
                if 'login' in page.url:
                    print("  ⚠️ 需要登入，請手動登入後繼續")
                    input("  按 Enter 繼續...")
                
                # 簡單滾動
                print("  滾動頁面...")
                for i in range(3):
                    if not safe_scroll(page, 600):
                        break
                    time.sleep(2)
                
                # 點擊展開留言（簡化版）
                print("  嘗試展開留言...")
                try:
                    # 找包含「則」或「more」的文字
                    more_links = page.locator('text=則').all()
                    for link in more_links[:3]:  # 只點前3個
                        try:
                            link.click()
                            time.sleep(2)
                        except:
                            pass
                except:
                    pass
                
                # 再次滾動
                for i in range(2):
                    safe_scroll(page, 500)
                    time.sleep(1)
                
                # 提取留言
                print("  提取留言...")
                comments = extract_comments_from_page(page, post_url)
                
                # 保存
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
                            print(f"    ✅ {comment['commenter_name']}")
                    except:
                        pass
                
                conn.commit()
                total_comments += saved
                print(f"  📊 保存 {saved}/{len(comments)} 條")
                
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
                continue
            
            time.sleep(3)
        
        browser.close()
    
    # 導出Excel
    cursor.execute('SELECT commenter_name, commenter_profile_url, comment_text, post_url, scraped_at FROM fb_leads')
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    df.to_excel(EXCEL_PATH, index=False, engine='openpyxl')
    
    print("\n" + "="*60)
    print("✅ 完成！")
    print("="*60)
    print(f"📊 新增: {total_comments} 條")
    print(f"📊 總計: {len(rows)} 條")
    print(f"📁 Excel: {EXCEL_PATH}")
    
    conn.close()

if __name__ == '__main__':
    main()
