#!/usr/bin/env python3
"""
Facebook 爬蟲 - CDP 版本 v2
直接連接到 OpenClaw 的 Chrome，共享已登入 session
根據實際 DOM 結構選擇留言
"""

from playwright.sync_api import sync_playwright
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import time
import re

# CDP 地址（OpenClaw Chrome）
CDP_URL = "http://127.0.0.1:18800"

# 目標群組
GROUP_ID = "945818406315161"
POST_ID = "2006837633546561"
POST_URL = f"https://www.facebook.com/groups/{GROUP_ID}/permalink/{POST_ID}/"

# 數據庫
DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_leads_final.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/fb_潛客_cdp.xlsx')
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
    cur.execute('''
        SELECT commenter_name, comment_text, post_url, scraped_at 
        FROM fb_leads ORDER BY scraped_at DESC
    ''')
    rows = cur.fetchall()
    
    import pandas as pd
    df = pd.DataFrame(rows, columns=['留言者', '留言內容', '貼文連結', '抓取時間'])
    
    EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(EXCEL_PATH, index=False, engine='openpyxl')
    shutil.copy(EXCEL_PATH, DESKTOP_EXCEL)
    return len(df)

def scrape_via_cdp():
    """通過 CDP 連接到 Chrome，提取留言"""
    
    with sync_playwright() as p:
        print("🔌 CDP 連接到 Chrome...")
        
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            print("✅ CDP 連接成功")
        except Exception as e:
            print(f"❌ CDP 連接失敗: {e}")
            return []
        
        # 找 Facebook 頁面
        context = browser.contexts[0]
        fb_page = None
        for page in context.pages:
            if 'facebook.com' in page.url:
                fb_page = page
                break
        
        if not fb_page:
            print("⚠️ 沒有 FB 頁面，創建新頁面")
            fb_page = context.new_page()
            fb_page.goto(POST_URL)
            fb_page.wait_for_load_state()
            time.sleep(3)
        
        print(f"📄 當前頁面: {fb_page.url}")
        
        # 等待對話框出現
        print("⏳ 等待留言對話框...")
        try:
            fb_page.wait_for_selector('dialog[role="dialog"]', timeout=10000)
            print("✅ 找到留言對話框")
        except:
            print("⚠️ 對話框未找到，繼續...")
        
        # 滾動載入更多留言
        print("📜 滾動頁面載入更多留言...")
        for i in range(5):
            fb_page.evaluate('window.scrollBy(0, 400)')
            time.sleep(1)
        
        # 提取留言
        leads = []
        
        try:
            # 找到對話框
            dialog = fb_page.query_selector('dialog[role="dialog"]')
            if not dialog:
                # 嘗試其他選擇器
                dialog = fb_page.query_selector('[aria-label*="帖子"]')
            
            if dialog:
                print("✅ 開始解析留言...")
                
                # 方法1：找所有 article（留言單元）
                articles = dialog.query_selector_all('article')
                print(f"   找到 {len(articles)} 個 article")
                
                seen_texts = set()
                
                for idx, article in enumerate(articles):
                    try:
                        # 找留言者名稱和內容
                        # 優先找有完整 href 的用戶連結
                        user_links = article.query_selector_all('a[href*="/groups/"][href*="/user/"]')
                        
                        if not user_links:
                            continue
                        
                        name = None
                        profile_url = None
                        text = None
                        
                        for ul in user_links:
                            href = ul.get_attribute('href') or ''
                            link_text = ul.inner_text().strip()
                            
                            # 跳過鏈接文字是時間、表情的
                            if re.match(r'^\d+[\u4e00-\u9fff]?(星期|月|日|年|小時|分鐘|前)?$', link_text):
                                continue
                            if link_text in ['分享', '回覆', '查看更多', '隱藏', '舉報']:
                                continue
                            if not link_text or len(link_text) < 2:
                                continue
                            if 'groups/' not in href or '/user/' not in href:
                                continue
                            
                            # 跳過管理員標記
                            if '管理員' in link_text:
                                continue
                            
                            # 檢查是否是「xxx的回應」格式（管理員回覆）
                            if '的回應' in link_text or '回覆' in link_text:
                                continue
                            
                            name = link_text
                            # 從 href 提取乾淨的 profile URL
                            profile_url = re.sub(r'\?.*$', '', href)
                            break
                        
                        if not name:
                            continue
                        
                        # 找留言內容 - 在用戶連結周圍找文字
                        # 很多時候文字就在同一個 link 或 div 裡
                        all_text_parts = []
                        
                        # 方法：找不包含其他連結的純文字
                        try:
                            parent = article.query_selector(':scope > div > div > div')
                            if parent:
                                # 獲取所有文字，但跳過子元素中的按鈕文字
                                def get_direct_text(element):
                                    text_parts = []
                                    for child in element.children:
                                        tag = child.tag_name.lower()
                                        if tag in ['button', 'a', 'img', 'svg', 'path', 'ul', 'ol', 'li']:
                                            continue
                                        text = child.inner_text().strip()
                                        if text and len(text) > 1:
                                            text_parts.append(text)
                                    return ' '.join(text_parts)
                                
                                raw_text = get_direct_text(parent)
                                if raw_text:
                                    all_text_parts.append(raw_text)
                        except:
                            pass
                        
                        # 方法2：直接在 article 層級找文字
                        if not all_text_parts:
                            try:
                                article_text = article.inner_text()
                                lines = [l.strip() for l in article_text.split('\n') if l.strip()]
                                
                                # 跳過第一行（用戶名）和時間
                                skip_patterns = ['的管理員', '的回應', '讚好', '回覆', '分享', '表達', '隱藏', '舉報']
                                
                                for line in lines[1:]:
                                    skip = False
                                    for pat in skip_patterns:
                                        if pat in line:
                                            skip = True
                                            break
                                    if skip:
                                        continue
                                    # 檢查是否太短（按鈕文字）
                                    if len(line) > 3 and not line.startswith('http'):
                                        all_text_parts.append(line)
                                        break
                            except:
                                pass
                        
                        if all_text_parts:
                            text = ' '.join(all_text_parts)[:500]
                        
                        # 跳過空留言
                        if not text or len(text) < 2:
                            continue
                        
                        # 去重
                        if text in seen_texts:
                            continue
                        seen_texts.add(text)
                        
                        leads.append({
                            'post_url': POST_URL,
                            'name': name,
                            'profile_url': profile_url or '',
                            'text': text
                        })
                        print(f"   [{idx+1}] {name}: {text[:50]}...")
                        
                    except Exception as e:
                        continue
                
                # 方法2：直接用 JS 提取所有留言（更準確）
                if len(leads) < 3:
                    print("\n🔄 嘗試 JS 提取模式...")
                    js_leads = fb_page.evaluate('''
                        () => {
                            const results = [];
                            const dialog = document.querySelector('dialog[role="dialog"]');
                            if (!dialog) return results;
                            
                            // 找所有留言 article
                            const articles = dialog.querySelectorAll('article');
                            articles.forEach(article => {
                                // 找用戶連結
                                const userLinks = article.querySelectorAll('a[href*="/groups/"][href*="/user/"]');
                                let name = '', profileUrl = '', text = '';
                                
                                userLinks.forEach(link => {
                                    const href = link.getAttribute('href') || '';
                                    const linkText = link.innerText.trim();
                                    
                                    // 跳過時間格式
                                    if (/^\\d+[星期月日年小時分鐘前]?$/.test(linkText)) return;
                                    // 跳過功能按鈕
                                    if (['分享','回覆','查看更多','隱藏','舉報','管理員'].some(k => linkText.includes(k))) return;
                                    // 跳過「xxx的回應」格式
                                    if (linkText.includes('的回應')) return;
                                    // 需要是 groups/user 格式
                                    if (!href.includes('/groups/') || !href.includes('/user/')) return;
                                    
                                    name = linkText;
                                    profileUrl = href.split('?')[0];
                                });
                                
                                if (!name) return;
                                
                                // 提取留言內容 - 找 link 後面的文字節點
                                const allInArticle = article.innerText.split('\\n').map(s => s.trim()).filter(s => s.length > 2);
                                // 留言內容通常是第三行之後
                                let foundName = false;
                                let textLines = [];
                                allInArticle.forEach(line => {
                                    if (line === name) { foundName = true; return; }
                                    if (foundName && !['的管理員','的回應','讚好：','回覆','分享','表達','隱藏','舉報','1 個心情','2 個心情','3 個心情','個心情'].some(k => line.includes(k))) {
                                        if (!/^\\d+[星期月日年小時分鐘前]?$/.test(line)) {
                                            textLines.push(line);
                                        }
                                    }
                                });
                                
                                if (textLines.length > 0) {
                                    text = textLines[0].substring(0, 500);
                                }
                                
                                if (name && text) {
                                    results.push({ name, profileUrl, text });
                                }
                            });
                            
                            return results;
                        }
                    ''')
                    
                    print(f"   JS 提取到 {len(js_leads)} 條")
                    for jl in js_leads:
                        if jl['text'] not in seen_texts and len(jl['text']) > 3:
                            seen_texts.add(jl['text'])
                            leads.append({
                                'post_url': POST_URL,
                                'name': jl['name'],
                                'profile_url': jl['profileUrl'],
                                'text': jl['text']
                            })
                            print(f"   [JS] {jl['name']}: {jl['text'][:50]}...")
            
        except Exception as e:
            print(f"解析失敗: {e}")
        
        return leads

def main():
    print("=" * 60)
    print("📘 Facebook CDP 爬蟲 v2")
    print("=" * 60)
    
    conn, cur = init_db()
    
    leads = scrape_via_cdp()
    
    if leads:
        print(f"\n📊 共提取 {len(leads)} 條留言")
        
        new_count = save_leads(conn, cur, leads)
        print(f"✅ 新增 {new_count} 條到數據庫")
        
        total = export_excel(cur)
        print(f"✅ Excel 導出: {total} 條")
        print(f"   📁 {DESKTOP_EXCEL}")
    else:
        print("\n⚠️ 沒有提取到留言")
    
    conn.close()
    print("\n👋 完成!")

if __name__ == "__main__":
    main()
