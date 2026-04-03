#!/usr/bin/env python3
"""
Browser 工具輔助腳本 - 幫助從瀏覽器提取留言
用於配合 browser action=snapshot 使用

使用方法:
1. 用 browser 工具打開 FB 帖子並滾動到最底
2. 運行此腳本分析當前頁面結構
3. 提取留言並保存到數據庫
"""

import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

def analyze_page_structure(html):
    """分析頁面結構"""
    soup = BeautifulSoup(html, 'lxml')
    
    results = {
        'dialogs': soup.find_all(attrs={'role': 'dialog'}),
        'articles': soup.find_all(attrs={'role': 'article'}),
        'groups_links': soup.find_all('a', href=lambda x: x and '/groups/' in x),
    }
    
    return results

def extract_comments_from_html(html, post_url):
    """從 HTML 提取留言"""
    soup = BeautifulSoup(html, 'lxml')
    comments = []
    seen_profiles = set()
    
    # 找對話框
    dialogs = soup.find_all(attrs={'role': 'dialog'})
    
    for dialog in dialogs:
        # 在對話框內找 article（留言）
        articles = dialog.find_all(attrs={'role': 'article'})
        
        for article in articles:
            # 找用戶連結
            links = article.find_all('a', href=lambda x: x and 'facebook.com' in x)
            
            for link in links:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                # 過濾
                if not name or len(name) < 2:
                    continue
                if name in ['讚', '回覆', '更多', '分享']:
                    continue
                if '/groups/' not in href and '/profile.php' not in href:
                    continue
                
                # 清理 URL
                clean_url = None
                groups_match = re.search(r'/groups/\d+/user/(\d+)', href)
                if groups_match:
                    clean_url = f"https://www.facebook.com/profile.php?id={groups_match.group(1)}"
                elif '/profile.php?id=' in href:
                    clean_url = re.match(r'(https://www\.facebook\.com/profile\.php\?id=\d+)', href)
                    clean_url = clean_url.group(1) if clean_url else None
                
                if not clean_url or clean_url in seen_profiles:
                    continue
                seen_profiles.add(clean_url)
                
                # 找留言內容
                text_divs = article.find_all('div', dir='auto')
                comment_text = ""
                for div in text_divs:
                    text = div.get_text(strip=True)
                    if text and text != name and len(text) > 3:
                        if not any(x in text for x in ['小時前', '分鐘前', '天前', '星期前']):
                            comment_text = text[:500]
                            break
                
                comments.append({
                    'name': name,
                    'url': clean_url,
                    'text': comment_text or "(無法提取)"
                })
    
    return comments

def save_comments(comments, post_url):
    """保存到數據庫"""
    db_path = Path.home() / '.openclaw/workspace/fb_leads_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    saved = 0
    for c in comments:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO fb_leads 
                (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (post_url, c['name'], c['url'], c['text'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            if cursor.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"  ⚠️ {c['name']}: {e}")
    
    conn.commit()
    conn.close()
    return saved

def export_to_excel():
    """導出到 Excel"""
    import pandas as pd
    
    db_path = Path.home() / '.openclaw/workspace/fb_leads_final.db'
    excel_path = Path.home() / f'.openclaw/workspace/fb_潛客_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT commenter_name, commenter_profile_url, comment_text, post_url, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    df.to_excel(excel_path, index=False, engine='openpyxl')
    
    return str(excel_path), len(df)

def main():
    print("="*60)
    print("📋 Browser 輔助提取工具")
    print("="*60)
    print()
    print("使用方法:")
    print("1. 用 browser 工具打開 FB 帖子")
    print("2. 滾動到最底，展開所有回覆")
    print("3. 使用 browser action=screenshot 保存截圖")
    print("4. 運行: python3 browser_extract.py <post_url>")
    print()
    print("或者直接粘貼 HTML 內容進行分析")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        post_url = sys.argv[1]
        print(f"📝 請粘貼頁面 HTML 內容到 stdin 或直接讀取截圖")
        print(f"   帖子URL: {post_url}")
    else:
        main()
