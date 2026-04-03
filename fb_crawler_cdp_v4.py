#!/usr/bin/env python3
"""
Facebook CDP 爬蟲 v4 - 使用 Playwright 導航 + 等待渲染
"""

from playwright.sync_api import sync_playwright
import json, sqlite3, shutil
from datetime import datetime
from pathlib import Path
import time

CDP_URL = "http://127.0.0.1:18800"
TARGET_POST = "https://www.facebook.com/groups/945818406315161/permalink/2006837633546561/"
DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_leads_cdp.db')
DESKTOP_EXCEL = Path.home() / 'Desktop' / 'fb_潛客_cdp.xlsx'

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
            lead['post_url'], lead['name'], lead['profile_url'], lead['text'],
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
    df.to_excel(DESKTOP_EXCEL, index=False, engine='openpyxl')
    return len(df)

EXTRACT_JS = """
() => {
    const results = [];
    const seen = new Set();
    
    // 找包含最多文字的 dialog
    const allDialogs = document.querySelectorAll('[role="dialog"]');
    let bestDialog = null;
    let bestLen = 0;
    
    for (const d of allDialogs) {
        const t = d.innerText || '';
        if (t.length > bestLen) {
            bestLen = t.length;
            bestDialog = d;
        }
    }
    
    if (!bestDialog) return { error: 'No dialog' };
    
    // 找所有 article（在 dialog 內或其 iframe 內）
    // 先在 dialog 內直接找
    let articles = Array.from(bestDialog.querySelectorAll('article'));
    
    // 如果 dialog 內沒有，遍歷所有 iframe
    if (articles.length === 0) {
        const iframes = bestDialog.querySelectorAll('iframe');
        for (const iframe of iframes) {
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
                if (iframeDoc) {
                    const ia = Array.from(iframeDoc.querySelectorAll('article'));
                    articles = articles.concat(ia);
                }
            } catch(e) {}
        }
    }
    
    console.log('Found ' + articles.length + ' articles');
    
    for (const article of articles) {
        const ariaLabel = article.getAttribute('aria-label') || '';
        
        // 只要頂級留言（xxx的回應），不要回覆
        if (!ariaLabel.includes('的回應') || ariaLabel.includes('回覆')) continue;
        
        const nameMatch = ariaLabel.match(/^(.+?)(?:的管理員)?的回應/);
        if (!nameMatch) continue;
        let name = nameMatch[1];
        
        // 跳過管理員
        if (name === 'Anthony Wong') continue;
        
        // 找 profile URL 和留言
        const userLinks = article.querySelectorAll('a[href*="/groups/"][href*="/user/"]');
        let profileUrl = '', text = '';
        
        for (const link of userLinks) {
            const href = link.getAttribute('href') || '';
            const linkText = link.innerText.trim();
            
            if (/^\\d+[星期月日年小時分鐘前]?$/.test(linkText)) continue;
            const skipWords = ['管理員','的回應','讚好：','回覆','分享','表達','隱藏','舉報','個心情','查看'];
            if (skipWords.some(k => linkText.includes(k))) continue;
            
            if (href.includes('/user/') && !href.includes('__cft__')) {
                profileUrl = href.split('?')[0];
            }
            
            if (linkText.length > 3 && linkText.length < 300 && !linkText.includes('http') && !linkText.includes('facebook')) {
                if (!text) text = linkText;
            }
        }
        
        // 取純文字
        if (!text || text.length < 2) {
            const lines = article.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 2);
            let skipMode = false;
            for (const line of lines) {
                if (line === name) { skipMode = true; continue; }
                if (skipMode) {
                    if (/^\\d+[星期月日年小時分鐘前]?$/.test(line)) continue;
                    if (['的管理員','的回應','讚好','回覆','分享','表達','隱藏','舉報','個心情','查看'].some(k => line.includes(k))) continue;
                    text = line;
                    break;
                }
            }
        }
        
        if (!text || text.length < 2) continue;
        
        const key = name + '|' + text.substring(0, 20);
        if (seen.has(key)) continue;
        seen.add(key);
        
        results.push({ name, profileUrl, text: text.substring(0, 500) });
    }
    
    return { count: results.length, posts: results, articlesFound: articles.length, dialogLen: bestLen };
}
"""

def main():
    print("=" * 60)
    print("📘 Facebook CDP 爬蟲 v4 (Playwright + 導航)")
    print("=" * 60)
    
    conn, cur = init_db()
    leads = []
    
    with sync_playwright() as p:
        print("🔌 CDP 連接...")
        browser = p.chromium.connect_over_cdp(CDP_URL)
        
        # 找或創建 Facebook page
        ctx = browser.contexts[0]
        fb_page = None
        for page in ctx.pages:
            if 'facebook.com' in page.url:
                fb_page = page
                break
        
        if not fb_page:
            print("❌ 沒有 Facebook 頁面")
            conn.close()
            return
        
        print(f"📄 當前: {fb_page.url}")
        
        # 導航到目標帖子
        print("🔗 導航到帖子...")
        fb_page.goto(TARGET_POST)
        fb_page.wait_for_load_state()
        time.sleep(3)
        
        # 滾動幾次讓內容載入
        print("📜 滾動載入...")
        for i in range(5):
            fb_page.evaluate('window.scrollBy(0, 500)')
            time.sleep(1)
        
        # 點擊帖子區域（確保焦點）
        try:
            # 找「留下回應」按鈕並點擊
            leave_comment_btn = fb_page.query_selector('button:has-text("留下回應")')
            if leave_comment_btn:
                print("✅ 點擊「留下回應」")
                leave_comment_btn.click()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ 點擊失敗: {e}")
        
        # 找並點擊「最相關」按鈕展開留言
        try:
            most_relevant = fb_page.query_selector('button:has-text("最相關")')
            if most_relevant:
                print("✅ 點擊「最相關」")
                most_relevant.click()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ 點擊最相關失敗: {e}")
        
        # 多次滾動 dialog
        print("📜 滾動 dialog...")
        for i in range(5):
            fb_page.evaluate('window.scrollBy(0, 300)')
            time.sleep(0.5)
        
        # 執行提取
        print("🔍 提取留言...")
        result = fb_page.evaluate(EXTRACT_JS)
        print(f"📊 結果: {json.dumps(result, ensure_ascii=False)}")
        
        for item in result.get('posts', []):
            leads.append({
                'post_url': TARGET_POST,
                'name': item['name'],
                'profile_url': item['profileUrl'] or '',
                'text': item['text']
            })
    
    if leads:
        print(f"\n📊 共 {len(leads)} 條留言")
        new_count = save_leads(conn, cur, leads)
        print(f"✅ 新增 {new_count} 條")
        total = export_excel(cur)
        print(f"✅ Excel: {total} 條 → {DESKTOP_EXCEL}")
    else:
        print("\n⚠️ 無留言")
    
    conn.close()
    print("\n👋 完成!")

if __name__ == "__main__":
    main()
