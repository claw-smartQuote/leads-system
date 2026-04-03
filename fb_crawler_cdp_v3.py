#!/usr/bin/env python3
"""
Facebook CDP 爬蟲 v3 - 連接到現有 Chrome 瀏覽器
使用 OpenClaw browser 的 CDP URL
"""

from playwright.sync_api import sync_playwright
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

CDP_URL = "http://127.0.0.1:18800"
TARGET_POST = "https://www.facebook.com/groups/945818406315161/permalink/2006837633546561/"
DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_leads_cdp.db')
DESKTOP_EXCEL = Path.home() / 'Desktop' / 'fb_潛客_cdp.xlsx'

EXTRACT_JS = """
() => {
    const results = [];
    const seen = new Set();
    
    // 找 dialog
    const allElements = document.querySelectorAll('[role="dialog"]');
    let targetDialog = null;
    
    for (const d of allElements) {
        const text = d.innerText || '';
        if (text.includes('Model Y') && text.length > 1000) {
            targetDialog = d;
            break;
        }
    }
    
    if (!targetDialog) {
        return { error: 'No dialog found' };
    }
    
    // 在 dialog 內找所有 article
    const articles = targetDialog.querySelectorAll('article');
    console.log('Found ' + articles.length + ' articles');
    
    for (const article of articles) {
        const ariaLabel = article.getAttribute('aria-label') || '';
        
        // 只需要「xxx的回應」格式（頂級留言），排除「回覆」
        if (!ariaLabel.includes('的回應') || ariaLabel.includes('回覆')) {
            continue;
        }
        
        const nameMatch = ariaLabel.match(/^(.+?)(?:的管理員)?的回應/);
        if (!nameMatch) continue;
        let name = nameMatch[1];
        
        // 跳過管理員
        if (name === 'Anthony Wong') continue;
        
        // 找 profile URL - 找第一個包含 /groups/xxx/user/xxx 的連結
        const userLinks = article.querySelectorAll('a[href*="/groups/"][href*="/user/"]');
        let profileUrl = '';
        let text = '';
        
        for (const link of userLinks) {
            const href = link.getAttribute('href') || '';
            const linkText = link.innerText.trim();
            
            // 跳過時間格式
            if (/^\\d+[星期月日年小時分鐘前]?$/.test(linkText)) continue;
            // 跳過按鈕文字
            const skipWords = ['管理員','的回應','讚好：','回覆','分享','表達','隱藏','舉報','個心情','查看'];
            if (skipWords.some(k => linkText.includes(k))) continue;
            
            if (href.includes('/user/') && !href.includes('__cft__')) {
                profileUrl = href.split('?')[0];
            }
            
            // 如果 link 文字夠長，可能是留言（但要排除連結中的長文字）
            if (linkText.length > 3 && linkText.length < 300 && !linkText.includes('http')) {
                if (!text) text = linkText;
            }
        }
        
        // 如果還是找不到文字，直接取 article 的純文字
        if (!text || text.length < 3) {
            const fullText = article.innerText;
            const lines = fullText.split('\\n').map(l => l.trim()).filter(l => l.length > 2);
            
            let skipMode = false;
            for (const line of lines) {
                if (line === name) { skipMode = true; continue; }
                if (skipMode) {
                    // 跳過時間、按鈕
                    if (/^\\d+[星期月日年小時分鐘前]?$/.test(line)) continue;
                    if (['的管理員','的回應','讚好','回覆','分享','表達','隱藏','舉報','個心情','查看'].some(k => line.includes(k))) continue;
                    text = line;
                    break;
                }
            }
        }
        
        if (!text || text.length < 2) continue;
        
        // 去重
        const key = name + '|' + text.substring(0, 20);
        if (seen.has(key)) continue;
        seen.add(key);
        
        results.push({
            name,
            profileUrl,
            text: text.substring(0, 500)
        });
    }
    
    return {
        count: results.length,
        posts: results,
        articlesTotal: articles.length
    };
}
"""

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
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
    return conn, cur

def save_leads(conn, cur, leads):
    new_count = 0
    for lead in leads:
        cur.execute('''
            INSERT OR IGNORE INTO fb_leads 
            (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            lead['post_url'],
            lead['name'],
            lead['profile_url'],
            lead['text'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        if cur.rowcount > 0:
            new_count += 1
    conn.commit()
    return new_count

def export_excel(cur):
    import pandas as pd
    cur.execute('SELECT commenter_name, comment_text, post_url, scraped_at FROM fb_leads ORDER BY scraped_at DESC')
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=['留言者', '留言內容', '貼文連結', '抓取時間'])
    DESKTOP_EXCEL.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(DESKTOP_EXCEL, index=False, engine='openpyxl')
    return len(df)

def main():
    print("=" * 60)
    print("📘 Facebook CDP 爬蟲 v3")
    print("=" * 60)
    
    conn, cur = init_db()
    leads = []
    
    with sync_playwright() as p:
        print("🔌 CDP 連接到 OpenClaw Chrome...")
        
        # 連接到現有 Chrome（使用 CDP URL）
        try:
            # 嘗試使用默認 CDP URL 連接
            browser = p.chromium.connect_over_cdp(CDP_URL)
            print("✅ CDP 連接成功")
        except Exception as e:
            print(f"❌ CDP 連接失敗: {e}")
            conn.close()
            return
        
        # 獲取所有 contexts
        print(f"📱 Browser contexts: {len(browser.contexts)}")
        
        # 遍歷所有 contexts 和 pages 找 Facebook
        fb_page = None
        for ctx in browser.contexts:
            print(f"   Context {id(ctx)}: {len(ctx.pages)} pages")
            for page in ctx.pages:
                print(f"   Page URL: {page.url[:80]}")
                if 'facebook.com' in page.url:
                    fb_page = page
                    print("   ✅ 找到 Facebook 頁面")
                    break
            if fb_page:
                break
        
        if not fb_page:
            print("❌ 沒有找到 Facebook 頁面")
            conn.close()
            return
        
        print(f"📄 使用頁面: {fb_page.url}")
        
        # 滾動頁面
        print("📜 滾動...")
        for _ in range(3):
            fb_page.evaluate('window.scrollBy(0, 300)')
            import time; time.sleep(0.5)
        
        # 執行 JS 提取
        print("🔍 執行 JS 提取...")
        try:
            result = fb_page.evaluate(EXTRACT_JS)
            print(f"📊 結果: {result}")
            
            for item in result.get('posts', []):
                leads.append({
                    'post_url': TARGET_POST,
                    'name': item['name'],
                    'profile_url': item['profileUrl'] or '',
                    'text': item['text']
                })
        except Exception as e:
            print(f"❌ JS 執行失敗: {e}")
    
    if leads:
        print(f"\n📊 共提取 {len(leads)} 條留言")
        new_count = save_leads(conn, cur, leads)
        print(f"✅ 新增 {new_count} 條到數據庫")
        total = export_excel(cur)
        print(f"✅ Excel: {total} 條 → {DESKTOP_EXCEL}")
    else:
        print("\n⚠️ 沒有提取到留言")
    
    conn.close()
    print("\n👋 完成!")

if __name__ == "__main__":
    main()
