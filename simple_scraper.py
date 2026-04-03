#!/usr/bin/env python3
"""
簡單爬蟲 - 使用 httpx + BeautifulSoup
適合無需登入的公開頁面
"""

import httpx
from bs4 import BeautifulSoup
import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path

CONFIG = {
    'DB_PATH': Path('/Users/claw/.openclaw/workspace/fb_leads_final.db'),
    'TIMEOUT': 30,
}

def fetch_page(url, headers=None):
    """獲取頁面 HTML"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-HK,zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        with httpx.Client(timeout=CONFIG['TIMEOUT'], follow_redirects=True) as client:
            response = client.get(url, headers=default_headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"⚠️ Fetch failed: {e}")
        return None

def parse_facebook_post(html):
    """解析 Facebook 帖子頁面（公開帖子）"""
    soup = BeautifulSoup(html, 'lxml')
    results = []
    
    # 嘗試找帖子內容
    articles = soup.find_all('article')
    print(f"  找到 {len(articles)} 個 article")
    
    # 找用戶名和內容
    for article in articles:
        # 找帖子內容
        paragraphs = article.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 20:  # 過濾短文字
                results.append(text)
    
    return results

def parse_28car(html):
    """解析 28car 汽車買賣頁面"""
    soup = BeautifulSoup(html, 'lxml')
    results = []
    
    # 找汽車列表
    items = soup.select('.item')
    for item in items:
        title = item.select_one('.title')
        price = item.select_one('.price')
        link = item.select_one('a')
        
        if title:
            results.append({
                'title': title.get_text(strip=True),
                'price': price.get_text(strip=True) if price else 'N/A',
                'link': link.get('href') if link else 'N/A'
            })
    
    return results

def save_to_db(post_url, commenters):
    """保存到數據庫"""
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    saved = 0
    for name, profile_url, comment_text in commenters:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO fb_leads 
                (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (post_url, name, profile_url, comment_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            if cursor.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"  ⚠️ 保存失敗: {e}")
    
    conn.commit()
    conn.close()
    return saved

def export_to_excel():
    """導出到 Excel"""
    import pandas as pd
    
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    cursor.execute('SELECT commenter_name, commenter_profile_url, comment_text, post_url, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cursor.fetchall()
    
    df = pd.DataFrame(rows, columns=['留言者名稱', '個人檔案連結', '留言內容', '貼文連結', '抓取時間'])
    excel_path = f'/Users/claw/.openclaw/workspace/fb_潛客_{datetime.now().strftime("%Y%m%d")}.xlsx'
    df.to_excel(excel_path, index=False, engine='openpyxl')
    
    conn.close()
    return excel_path, len(df)

def scrape_url(url, source_type='auto'):
    """自動識別並爬取頁面"""
    print(f"\n🌐 抓取: {url}")
    
    html = fetch_page(url)
    if not html:
        print("❌ 無法獲取頁面")
        return []
    
    # 根據 URL 自動識別來源
    if '28car' in url:
        print("📋 識別為 28car 頁面")
        return parse_28car(html)
    elif 'facebook' in url:
        print("📋 識別為 Facebook 頁面")
        return parse_facebook_post(html)
    else:
        # 通用解析
        print("📋 使用通用解析")
        soup = BeautifulSoup(html, 'lxml')
        texts = [p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 50]
        return texts

def main():
    print("="*60)
    print("📡 簡單爬蟲 - httpx + BeautifulSoup")
    print("="*60)
    print("\n用法:")
    print("  python3 simple_scraper.py <url>")
    print("\n範例:")
    print("  python3 simple_scraper.py https://example.com")
    print("  python3 simple_scraper.py https://www.28car.com/...")
    print()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        results = scrape_url(url)
        print(f"\n✅ 抓到 {len(results)} 項結果")
        for i, r in enumerate(results[:10], 1):
            print(f"  {i}. {str(r)[:80]}...")
    else:
        main()
