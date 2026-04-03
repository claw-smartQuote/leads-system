#!/usr/bin/env python3
"""
Facebook CDP 爬蟲 - 直接使用 browser tool 的 CDP endpoint
通過 REST CDP API 直接注入 JS 提取留言
"""

import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.parse

# OpenClaw CDP 地址
CDP_DEBUG_PORT = 18800
CDP_URL = f"http://127.0.0.1:{CDP_DEBUG_PORT}"

TARGET_POST = "https://www.facebook.com/groups/945818406315161/permalink/2006837633546561/"
DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_leads_cdp.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/fb_潛客_cdp.xlsx')
DESKTOP_EXCEL = Path.home() / 'Desktop' / 'fb_潛客_cdp.xlsx'

def cdp_send(cmd):
    """通過 CDP REST API 發送命令"""
    data = json.dumps({"id": 1, "method": cmd["method"], "params": cmd.get("params", {})}).encode()
    req = urllib.request.Request(
        f"{CDP_URL}/json",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

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
    cur.execute('''
        SELECT commenter_name, comment_text, post_url, scraped_at 
        FROM fb_leads ORDER BY scraped_at DESC
    ''')
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=['留言者', '留言內容', '貼文連結', '抓取時間'])
    EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(EXCEL_PATH, index=False, engine='openpyxl')
    shutil.copy(EXCEL_PATH, DESKTOP_EXCEL)
    return len(df)

# ============ JS 提取腳本 ============
EXTRACT_JS = """
() => {
    const results = [];
    
    // 找到對話框
    const dialogs = document.querySelectorAll('dialog[role="dialog"]');
    let dialog = null;
    dialogs.forEach(d => {
        if (d.innerText.includes('的回應') || d.innerText.includes('帖子')) {
            dialog = d;
        }
    });
    
    if (!dialog) {
        // 嘗試其他方式找
        const allDialogs = document.querySelectorAll('[role="dialog"]');
        allDialogs.forEach(d => {
            const text = d.innerText || '';
            if (text.length > 500 && text.includes('Model Y')) {
                dialog = d;
            }
        });
    }
    
    if (!dialog) {
        return { error: 'No dialog found', count: 0, posts: [] };
    }
    
    // 找到「最相關」按鈕下的 toolbar
    const toolbars = dialog.querySelectorAll('div[role="toolbar"]');
    let targetToolbar = null;
    toolbars.forEach(t => {
        if (t.innerText.includes('最相關')) {
            targetToolbar = t;
        }
    });
    
    // 如果找不到 toolbar，直接在 dialog 裡找 article
    const articles = targetToolbar ? targetToolbar.querySelectorAll(':scope > article') : dialog.querySelectorAll('article');
    
    console.log('Found ' + articles.length + ' articles');
    
    // 只取最相關排序下的直接 article（頂級留言）
    // 這些 article 的 aria-label 包含「xxx的回應」
    const seen = new Set();
    
    // 在 toolbar 層級找 article
    const topLevel = [];
    if (targetToolbar) {
        // toolbar 的直接 article 子元素
        const children = targetToolbar.children;
        for (const child of children) {
            if (child.tagName === 'ARTICLE') {
                const ariaLabel = child.getAttribute('aria-label') || '';
                if (ariaLabel.includes('的回應') && !ariaLabel.includes('回覆')) {
                    topLevel.push(child);
                }
            }
        }
    }
    
    console.log('Found ' + topLevel.length + ' top-level comments');
    
    // 提取每條留言
    for (const article of topLevel) {
        try {
            const ariaLabel = article.getAttribute('aria-label') || '';
            
            // 提取名字：aria-label 格式是「xxx的回應4星期前」
            const nameMatch = ariaLabel.match(/^(.+?)的回應/);
            if (!nameMatch) continue;
            const name = nameMatch[1];
            
            // 跳過管理員
            if (name === 'Anthony Wong') continue;
            
            // 提取 profile URL：找 article 內第一個 /groups/xxx/user/xxx 的連結
            const userLink = article.querySelector('a[href*="/groups/"][href*="/user/"]');
            let profileUrl = '';
            if (userLink) {
                const href = userLink.getAttribute('href') || '';
                profileUrl = href.split('?')[0];
            }
            
            // 提取留言內容
            // 方法：在 article 內找文字
            let text = '';
            
            // 1. 找包含長文字的元素
            const allLinks = article.querySelectorAll('a[href*="/groups/"][href*="/user/"]');
            for (const link of allLinks) {
                const linkText = link.innerText.trim();
                // 這個連結的文字就是留言內容
                if (linkText && linkText.length > 3 && 
                    !linkText.match(/^\\d+[星期月日年小時分鐘前]?$/) &&
                    !linkText.includes('的管理員') &&
                    !linkText.includes('的回應') &&
                    linkText !== name) {
                    text = linkText;
                    break;
                }
            }
            
            // 2. 如果還是找不到，在 article 層級取 innerText
            if (!text || text.length < 3) {
                const articleText = article.innerText;
                const lines = articleText.split('\\n').filter(l => l.trim().length > 3);
                
                let foundName = false;
                for (const line of lines) {
                    const trimmed = line.trim();
                    // 跳過名字行
                    if (trimmed === name || trimmed.includes(name + ' ')) {
                        foundName = true;
                        continue;
                    }
                    // 跳過時間
                    if (trimmed.match(/^\\d+[星期月日年小時分鐘前]?$/) || trimmed.match(/^[0-9]+小時/)) {
                        continue;
                    }
                    // 跳過按鈕文字
                    const skipWords = ['的管理員','的回應','讚好','回覆','分享','表達','隱藏','舉報','個心情','查看'];
                    if (skipWords.some(w => trimmed.includes(w))) {
                        continue;
                    }
                    text = trimmed;
                    break;
                }
            }
            
            if (!text || text.length < 2) continue;
            
            // 去重
            if (seen.has(name + '|' + text.substring(0, 30))) continue;
            seen.add(name + '|' + text.substring(0, 30));
            
            results.push({
                name,
                profileUrl,
                text: text.substring(0, 500)
            });
        } catch (e) {
            console.error('Error processing article:', e);
        }
    }
    
    return {
        count: results.length,
        posts: results,
        dialogFound: true,
        articlesFound: articles.length,
        topLevelFound: topLevel.length
    };
}
"""

def run_extraction():
    """通過 CDP 執行 JS"""
    print("🔌 嘗試 CDP 連接...")
    
    # 首先檢查 CDP 是否可用
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{CDP_DEBUG_PORT}/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode())
            print(f"✅ CDP 可用，找到 {len(targets)} 個 target")
    except Exception as e:
        print(f"❌ CDP 連接失敗: {e}")
        return []
    
    # 使用 CDPRuntime.evaluate 執行 JS
    # 需要先綁定到正確的 target (Facebook page)
    result = cdp_send({
        "method": "Runtime.evaluate",
        "params": {
            "expression": EXTRACT_JS,
            "returnByValue": True
        }
    })
    
    if "error" in result:
        print(f"❌ 執行失敗: {result['error']}")
        return []
    
    try:
        result_data = result.get("result", {}).get("result", {})
        if result_data.get("type") == "object" and "value" in result_data:
            data = result_data["value"]
        elif result_data.get("type") == "string":
            data = json.loads(result_data["value"])
        else:
            print(f"⚠️ 無法解析結果: {result_data}")
            return []
        
        print(f"📊 結果: {data}")
        
        leads = []
        for item in data.get("posts", []):
            leads.append({
                'post_url': TARGET_POST,
                'name': item['name'],
                'profile_url': item['profileUrl'] or '',
                'text': item['text']
            })
        
        return leads
        
    except Exception as e:
        print(f"❌ 解析結果失敗: {e}")
        print(f"原始結果: {result}")
        return []

def main():
    print("=" * 60)
    print("📘 Facebook CDP 爬蟲 (REST CDP)")  
    print("=" * 60)
    
    conn, cur = init_db()
    leads = run_extraction()
    
    if leads:
        print(f"\n📊 共提取 {len(leads)} 條留言")
        new_count = save_leads(conn, cur, leads)
        print(f"✅ 新增 {new_count} 條到數據庫")
        total = export_excel(cur)
        print(f"✅ Excel: {total} 條 → {DESKTOP_EXCEL}")
    else:
        print("\n⚠️ 沒有提取到留言")
    
    conn.close()

if __name__ == "__main__":
    main()
