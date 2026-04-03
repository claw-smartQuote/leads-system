#!/usr/bin/env python3
"""
Facebook 爬蟲 - CDP 版本
直接連接到 OpenClaw 的 Chrome 瀏覽器，共享已登入 session
"""

from playwright.sync_api import sync_playwright
import json
import sqlite3
from datetime import datetime
import time

# CDP 地址
CDP_URL = "http://127.0.0.1:18800"

def get_fb_comments_via_cdp():
    """通過 CDP 連接 Chrome 提取 Facebook 留言"""
    
    with sync_playwright() as p:
        print("🔌 嘗試 CDP 連接到 Chrome...")
        
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            print("✅ CDP 連接成功!")
        except Exception as e:
            print(f"❌ CDP 連接失敗: {e}")
            return []
        
        context = browser.contexts[0]
        
        # 找到 Facebook 頁面
        fb_page = None
        for page in context.pages:
            if 'facebook.com' in page.url:
                fb_page = page
                break
        
        if not fb_page:
            print("⚠️ 沒有找到 Facebook 頁面，創建新頁面")
            fb_page = context.new_page()
            fb_page.goto("https://www.facebook.com/groups/945818406315161/permalink/2006837633546561/")
            fb_page.wait_for_load_state()
        
        print(f"📄 當前頁面: {fb_page.url}")
        
        # 滾動頁面載入更多內容
        print("📜 滾動頁面...")
        for i in range(8):
            fb_page.evaluate('window.scrollBy(0, 600)')
            time.sleep(2)
        
        # 提取留言
        comments = []
        
        try:
            # 嘗試找到彈出對話框（帖子詳情）
            dialog = fb_page.query_selector('[role="dialog"]')
            if dialog:
                print("✅ 找到帖子對話框")
                
                # 提取所有留言
                articles = dialog.query_selector_all('article')
                print(f"找到 {len(articles)} 條留言")
                
                for article in articles:
                    try:
                        # 留言者名稱
                        name_elem = article.query_selector('a[href*="/user/"]')
                        name = name_elem.inner_text() if name_elem else "Unknown"
                        
                        # 留言內容
                        text_elem = article.query_selector('[data-ad-preview="message"]')
                        text = text_elem.inner_text() if text_elem else ""
                        
                        if name and text:
                            comments.append({
                                'name': name,
                                'text': text[:500]
                            })
                    except Exception as e:
                        continue
            else:
                print("⚠️ 沒有找到帖子對話框")
        except Exception as e:
            print(f"提取留言失敗: {e}")
        
        return comments, fb_page

def save_to_db(comments):
    """保存到數據庫"""
    db_path = '/Users/claw/.openclaw/workspace/fb_leads_final.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    new_count = 0
    for c in comments:
        cursor.execute('''
            INSERT OR IGNORE INTO fb_leads 
            (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            "https://www.facebook.com/groups/945818406315161/permalink/2006837633546561/",
            c['name'],
            f"https://www.facebook.com/groups/945818406315161/user/0/",
            c['text'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        if cursor.rowcount > 0:
            new_count += 1
    
    conn.commit()
    conn.close()
    
    return new_count

def export_to_excel():
    """導出到 Excel"""
    import pandas as pd
    
    db_path = '/Users/claw/.openclaw/workspace/fb_leads_final.db'
    conn = sqlite3.connect(db_path)
    
    df = pd.read_sql_query('''
        SELECT commenter_name, comment_text, post_url, scraped_at 
        FROM fb_leads 
        ORDER BY scraped_at DESC
    ''', conn)
    
    conn.close()
    
    output_path = '/Users/claw/.openclaw/workspace/fb_潛客名單_final.xlsx'
    df.to_excel(output_path, index=False, engine='openpyxl')
    
    # 複製到桌面
    import shutil
    desktop = '/Users/claw/Desktop/fb_潛客名單_final.xlsx'
    shutil.copy(output_path, desktop)
    
    return len(df), output_path, desktop

if __name__ == "__main__":
    print("=" * 60)
    print("📘 Facebook 爬蟲 (CDP 版本)")
    print("=" * 60)
    
    comments, page = get_fb_comments_via_cdp()
    
    if comments:
        print(f"\n📊 提取到 {len(comments)} 條留言")
        
        new_count = save_to_db(comments)
        print(f"✅ 新增 {new_count} 條到數據庫")
        
        total, xlsx_path, desktop_path = export_to_excel()
        print(f"✅ 導出完成: 共 {total} 條")
        print(f"   Excel: {xlsx_path}")
        print(f"   桌面: {desktop_path}")
    else:
        print("⚠️ 沒有提取到留言")
    
    print("\n👋 完成!")
