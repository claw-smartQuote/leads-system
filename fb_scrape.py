#!/usr/bin/env python3
"""
Facebook 爬蟲 - 讀取登入狀態做嘢
發現登入失效時自動發出 WhatsApp 警報
"""

import re
import time
import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError
import sys

# ========== 配置 ==========
POST_URLS = [
    'https://www.facebook.com/Zhuhaiinsurance/posts/pfbid0257WFhkLDQuK2WZEhHVsYCW9xZYJUQWxRKw3uJiH2X7Thj9SQp4E3w6CnLRcB5bWjl',
    # 可以加入更多帖子URL
]

DB_PATH = Path('/Users/claw/.openclaw/workspace/fb_leads.db')
EXCEL_PATH = Path('/Users/claw/.openclaw/workspace/fb_潛客_自動.xlsx')
STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'
COOKIE_PATH = Path.home() / '.fb_crawler' / 'fb_cookies.json'

# WhatsApp 通知
WHATSAPP_TO = "+85221101144"  # 你的號碼

# ========== WhatsApp 警報 ==========
def send_alert(message: str):
    """通過 OpenClaw message 工具發出 WhatsApp 警報"""
    print(f"\n⚠️ 發出警報: {message}")
    
    # 寫入觸發文件
    trigger_dir = Path.home() / '.openclaw' / 'workspace' / 'alerts'
    trigger_dir.mkdir(parents=True, exist_ok=True)
    
    trigger_file = trigger_dir / f"fb_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    alert_data = {
        "to": WHATSAPP_TO,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "type": "fb_login_expired"
    }
    
    with open(trigger_file, 'w', encoding='utf-8') as f:
        json.dump(alert_data, f, ensure_ascii=False, indent=2)
    
    print(f"   📁 警報已保存: {trigger_file}")

# ========== 數據庫 ==========
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
            scraped_at TEXT,
            UNIQUE(post_url, commenter_profile_url)
        )
    ''')
    conn.commit()
    return conn, cursor

def save_to_excel():
    """導出到 Excel"""
    conn, cursor = init_database()
    df = pd.read_sql_query("SELECT * FROM fb_leads ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        df.to_excel(EXCEL_PATH, index=False)
        print(f"✅ 已導出 {len(df)} 條數據到: {EXCEL_PATH}")

# ========== 檢查登入狀態 ==========
def check_login_required(page) -> bool:
    """檢查是否需要登入"""
    current_url = page.url.lower()
    
    # 检查是否在登入頁
    if 'login' in current_url:
        return True
    
    # 檢查是否有登入提示元素
    try:
        # 尋找登入按鈕或登入表單
        login_forms = page.locator('form[action*="login"]').count()
        if login_forms > 0:
            return True
    except:
        pass
    
    return False

def wait_for_login(page, timeout=30000):
    """等待用戶手動登入"""
    print("\n" + "="*60)
    print("⚠️ 偵測到需要登入！")
    print("="*60)
    print("請喺瀏覽器中完成登入...")
    print("登入成功後我会自動繼續\n")
    
    try:
        # 每5秒檢查一次是否已登入
        start_time = time.time()
        while time.time() - start_time < timeout / 1000:
            page.wait_for_timeout(5000)
            if not check_login_required(page):
                print("✅ 登入成功！繼續爬取...")
                return True
        return False
    except Exception as e:
        print(f"等待登入時出錯: {e}")
        return False

# ========== 爬取邏輯 ==========
def safe_scroll(page, amount=800):
    try:
        page.evaluate(f'window.scrollBy(0, {amount})')
        return True
    except:
        return False

def extract_comments_from_page(page, post_url):
    comments = []
    seen = set()
    
    try:
        articles = page.locator('[role="article"]').all()
        
        for article in articles:
            try:
                links = article.locator('a').all()
                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=200) or ''
                        name = link.inner_text(timeout=200).strip()
                        
                        if not name or len(name) < 2 or len(name) > 40:
                            continue
                        if name in ['讚', '回覆', 'Like', 'Reply', '更多', '分享']:
                            continue
                        
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
                        
                        comment_text = ""
                        try:
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
                            'comment_text': comment_text,
                            'scraped_at': datetime.now().isoformat()
                        })
                    except:
                        continue
            except:
                continue
    except Exception as e:
        print(f"提取留言出錯: {e}")
    
    return comments

def save_comments(comments):
    if not comments:
        return
    
    conn, cursor = init_database()
    
    for c in comments:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO fb_leads 
                (post_url, commenter_name, commenter_profile_url, comment_text, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (c['post_url'], c['commenter_name'], c['commenter_profile_url'], 
                  c['comment_text'], c['scraped_at']))
        except Exception as e:
            print(f"保存出錯: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ 已保存 {len(comments)} 條留言")

# ========== 主程式 ==========
def main():
    print("="*60)
    print("📘 Facebook 爬蟲 (自動登入檢測版)")
    print("="*60)
    
    # 檢查 Storage State 是否存在
    if not STORAGE_STATE_PATH.exists():
        print("\n❌ 未找到登入狀態！")
        print(f"   請先運行: python3 fb_login_new.py")
        
        # 發出警報
        alert_msg = """⚠️ *FB 爬蟲需要登入*

❌ 未找到登入狀態
👉 請运行 fb_login_new.py 進行登入

📍 路徑: ~/.fb_crawler/fb_storage_state.json
"""
        send_alert(alert_msg)
        sys.exit(1)
    
    print(f"\n✅ 找到登入狀態: {STORAGE_STATE_PATH}")
    
    with sync_playwright() as p:
        try:
            # 加載 Storage State
            print("🚀 啟動瀏覽器...")
            
            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # 使用保存既 Storage State
            context = browser.new_context(
                viewport={'width': 1400, 'height': 900},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-HK',
                timezone_id='Asia/Hong_Kong',
                storage_state=str(STORAGE_STATE_PATH)
            )
            
            # 隱藏自動化痕跡
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)
            
            page = context.new_page()
            
            # 訪問第一個帖子
            post_url = POST_URLS[0]
            print(f"\n🌐 訪問帖子: {post_url[:50]}...")
            
            try:
                page.goto(post_url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                print(f"訪問失敗: {e}")
            
            # ===== 關鍵：檢查是否需要登入 =====
            if check_login_required(page):
                # 發出 WhatsApp 警報
                alert_msg = """⚠️ *FB 爬蟲登入過期！*

❌ Cookie/Storage State 已過期
⚠️ 請重新登入

👉 运行以下命令:
python3 fb_login_new.py
"""
                send_alert(alert_msg)
                
                # 等待用戶手動登入
                if not wait_for_login(page):
                    print("❌ 等待登入超時")
                    browser.close()
                    sys.exit(1)
            
            # 正常爬取流程
            print("\n🔍 開始爬取留言...")
            
            # 滾動頁面
            for _ in range(5):
                safe_scroll(page, 800)
                page.wait_for_timeout(1000)
            
            # 提取留言
            comments = extract_comments_from_page(page, post_url)
            print(f"📊 呢次爬到 {len(comments)} 條留言")
            
            # 保存
            save_comments(comments)
            
            # 導出 Excel
            save_to_excel()
            
            browser.close()
            
            print("\n" + "="*60)
            print("🎉 爬取完成！")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")
            
            # 發出錯誤警報
            alert_msg = f"""⚠️ *FB 爬蟲出錯*

❌ 錯誤: {str(e)[:100]}

請檢查系統狀態
"""
            send_alert(alert_msg)
            sys.exit(1)

if __name__ == '__main__':
    main()
