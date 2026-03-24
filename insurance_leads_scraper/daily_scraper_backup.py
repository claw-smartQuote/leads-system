#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合爬蟲系統 - 28car.com + Facebook
每天自動抓取至少100條有效數據
作者: AI Assistant
版本: 2.0
"""

import os
import sys

# 添加用戶 site-packages 路徑（解決 macOS 用戶安裝的依賴問題）
USER_SITE_PACKAGES = os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages')
if USER_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, USER_SITE_PACKAGES)

import time
import random
import re
import sqlite3
import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path

# 嘗試導入 Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright 未安裝，28car 模塊將不可用")

# 嘗試導入 undetected_chromedriver
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    print("⚠️ undetected-chromedriver 未安裝，Facebook 模塊將不可用")

# ============ 全局配置 ============
TARGET_COUNT = 100  # 目標數據量
MIN_SLEEP = 2
MAX_SLEEP = 5
DATA_DIR = Path.home() / "Desktop" / "汽車保險潛客數據"
DATA_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime('%Y%m%d')
RAW_EXCEL_28CAR = DATA_DIR / f"本地_28car資料_{TODAY}.xlsx"
RAW_EXCEL_FB = DATA_DIR / f"本地_Facebook資料_{TODAY}.xlsx"
CLEAN_EXCEL = DATA_DIR / f"本地_全部資料_{TODAY}.xlsx"
DB_PATH = DATA_DIR / f"daily_scraper_{TODAY}.db"

# Facebook 配置
FB_GROUPS = [
    "https://www.facebook.com/groups/hongkongcar",
    "https://www.facebook.com/groups/香港汽車買賣",
    "https://www.facebook.com/groups/852carmember",
    "https://www.facebook.com/groups/港車北上",
]

# 擴展關鍵詞，針對港車北上
FB_KEYWORDS_POSTS = ['港車北上', '北上', '港珠澳', '大灣區', '深圳', '珠海', '廣東', '內地車', '跨境']
FB_KEYWORDS_INSURANCE = ['車險', '汽車保險', '保險', '第三者', '全保', '驗車', '年審', '續保']
FB_KEYWORDS_TRADE = ['買車', '賣車', '換車', '放車', '求車', '收車']
FB_KEYWORDS = FB_KEYWORDS_POSTS + FB_KEYWORDS_INSURANCE + FB_KEYWORDS_TRADE

# ============ 數據庫管理 ============
class DatabaseManager:
    """統一數據庫管理"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 28car 數據表（添加電郵欄位）
        c.execute('''
            CREATE TABLE IF NOT EXISTS car28_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                email TEXT,
                model TEXT,
                source TEXT,
                created_at TEXT
            )
        ''')
        
        # Facebook 數據表（添加電話和電郵欄位）
        c.execute('''
            CREATE TABLE IF NOT EXISTS fb_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                phone TEXT,
                email TEXT,
                post_content TEXT,
                keyword TEXT,
                group_url TEXT,
                content_type TEXT DEFAULT 'post',
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_28car(self, phone, email, model, source):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT OR IGNORE INTO car28_leads (phone, email, model, source, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (phone, email, model, source, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def save_fb(self, user_name, phone, email, post_content, keyword, group_url, content_type='post'):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # 如果有電話號碼或電郵，也保存到 28car 表中統一管理
            if phone or email:
                c.execute('''
                    INSERT OR IGNORE INTO car28_leads (phone, email, model, source, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (phone or '', email or '', f'FB:{user_name}', f'Facebook-{content_type}-{keyword}', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            c.execute('''
                INSERT OR IGNORE INTO fb_leads (user_name, phone, email, post_content, keyword, group_url, content_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_name, phone, email, post_content[:200], keyword, group_url, content_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_total_count(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM car28_leads")
        car28_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM fb_leads")
        fb_count = c.fetchone()[0]
        conn.close()
        return car28_count + fb_count
    
    def get_28car_count(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM car28_leads")
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def get_fb_count(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM fb_leads")
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def export_excel(self):
        conn = sqlite3.connect(self.db_path)
        
        # 導出 28car 電話和電郵（包含所有欄位）
        df_28car = pd.read_sql("SELECT id 編號, phone 電話, email 電郵, model 車型, source 來源, created_at 創建時間 FROM car28_leads", conn)
        
        # 導出 Facebook 潛客（包括有電話/電郵的）
        df_fb = pd.read_sql("SELECT user_name 用戶名, phone 電話, email 電郵, keyword 關鍵詞, group_url 來源, content_type 內容類型, post_content 帖子內容 FROM fb_leads", conn)
        
        # 導出 Facebook 有電話或電郵的數據
        df_fb_phones = pd.read_sql("SELECT phone 電話, email 電郵, user_name 用戶名, keyword 關鍵詞, group_url 來源, content_type 內容類型 FROM fb_leads WHERE (phone IS NOT NULL AND phone != '') OR (email IS NOT NULL AND email != '')", conn)
        
        # 按類型統計
        df_fb_posts = df_fb[df_fb['內容類型'] == 'post'] if '內容類型' in df_fb.columns else pd.DataFrame()
        df_fb_comments = df_fb[df_fb['內容類型'] == 'comment'] if '內容類型' in df_fb.columns else pd.DataFrame()
        
        # 清理非法字符（Excel 不允許的控制字符）
        def clean_illegal_chars(df):
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].apply(lambda x: ''.join(c for c in str(x) if ord(c) >= 32 or c in '\t\n\r') if pd.notna(x) else x)
            return df
        
        # 分開導出 28car 數據
        df_28car = clean_illegal_chars(df_28car)
        df_28car.to_excel(RAW_EXCEL_28CAR, index=False, sheet_name='28car電話')
        
        # 分開導出 Facebook 數據（如果有數據）
        if not df_fb.empty:
            df_fb = clean_illegal_chars(df_fb)
            with pd.ExcelWriter(RAW_EXCEL_FB, engine='openpyxl') as writer:
                df_fb.to_excel(writer, sheet_name='Facebook潛客', index=False)
                if not df_fb_phones.empty:
                    df_fb_phones = clean_illegal_chars(df_fb_phones)
                    df_fb_phones.to_excel(writer, sheet_name='Facebook電話', index=False)
        
        # 清洗後資料（合併 28car 和 Facebook 的電話，包含所有欄位）
        df_28_phones = df_28car[df_28car['電話'].notna()].copy() if not df_28car.empty else pd.DataFrame()
        df_fb_only_phones = df_fb[df_fb['電話'].notna()][['電話', '電郵', '用戶名', '關鍵詞', '來源', '內容類型', '帖子內容']].copy() if not df_fb.empty else pd.DataFrame()
        
        # 合併並去重（根據電話）
        df_all_phones = pd.concat([df_28_phones, df_fb_only_phones], ignore_index=True)
        df_clean = df_all_phones.drop_duplicates(subset=['電話'], keep='first')
        df_clean = clean_illegal_chars(df_clean)
        df_clean.to_excel(CLEAN_EXCEL, index=False, sheet_name='清洗後資料')
        
        conn.close()
        
        # 返回統計
        car28_count = len(df_28car)
        fb_count = len(df_fb)
        fb_phone_count = len(df_fb_phones) if not df_fb_phones.empty else 0
        fb_post_count = len(df_fb_posts)
        fb_comment_count = len(df_fb_comments)
        total_phones = len(df_clean)
        
        return car28_count, fb_count, fb_phone_count, fb_post_count, fb_comment_count, total_phones

# ============ 28car 爬蟲模塊 ============
class Car28Scraper:
    """28car.com 爬蟲器"""
    
    def __init__(self, db):
        self.db = db
        self.browser = None
        self.page = None
    
    def init_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            return False
        try:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(headless=False)
            self.page = self.browser.new_page(viewport={'width': 1400, 'height': 900})
            return True
        except Exception as e:
            print(f"❌ 28car 瀏覽器啟動失敗: {e}")
            return False
    
    def close_browser(self):
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
    
    def random_delay(self):
        time.sleep(random.uniform(MIN_SLEEP, MAX_SLEEP))
    
    def scrape_page(self, page_num):
        try:
            url = f"https://www.28car.com/sell_lst.php" + (f"?pg={page_num}" if page_num > 1 else "")
            print(f"  📄 爬取第 {page_num} 頁...")
            
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            self.random_delay()
            
            # 找內容 frame
            target_frame = None
            for frame in self.page.frames:
                try:
                    if '28car.com' in frame.url and len(frame.inner_text('body', timeout=2000)) > 30000:
                        target_frame = frame
                        break
                except:
                    continue
            
            if not target_frame:
                return 0
            
            # 獲取整頁 HTML 和文本內容
            html_content = target_frame.content()
            text_content = target_frame.inner_text('body')
            
            # === 新方法：基於車盤區塊的分析 ===
            # 1. 先找到所有車盤區塊（通過編號 sxxxxx 識別）
            # 2. 從每個區塊中提取車型和電話
            
            new_count = 0
            
            # 定義品牌列表（中英文）
            all_brands = [
                # 中文品牌
                '奧迪', '寶馬', '平治', 'Mercedes', '豐田', '本田', '凌志', 'Lexus',
                '日產', 'Nissan', '萬事得', 'Mazda', '現代', 'Hyundai', '福士', 'Volkswagen',
                '福特', 'Ford', '保時捷', 'Porsche', '特斯拉', 'Tesla', '迷你', 'Mini',
                '路虎', 'Land Rover', '積架', 'Jaguar', '瑪莎拉蒂', 'Maserati',
                '法拉利', 'Ferrari', '林寶堅尼', 'Lamborghini', '麥拿倫', 'McLaren',
                '勞斯萊斯', 'Rolls-Royce', '賓利', 'Bentley', '蓮花', 'Lotus',
                '雪鐵龍', 'Citroen', '雷諾', 'Renault', '標緻', 'Peugeot',
                '鈴木', 'Suzuki', '三菱', 'Mitsubishi', '斯巴魯', 'Subaru',
                '英菲尼迪', 'Infiniti', '謳歌', 'Acura', '吉普', 'Jeep', '富豪', 'Volvo',
                # 英文品牌
                'Audi', 'BMW', 'Benz', 'Toyota', 'Honda', 'Hyundai', 'Kia', '起亞',
                'Chevrolet', 'GMC', 'Cadillac', 'Lincoln', 'Chrysler', 'Dodge',
                'Skoda', 'SEAT', 'Fiat', 'Alfa Romeo', 'Volvo', 'Jaguar',
            ]
            
            # 方法：掃描所有行，識別車盤區塊
            lines = text_content.split('\n')
            
            # 找到所有包含車盤資訊的行索引
            car_blocks = []
            current_block = {'start': 0, 'lines': []}
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 檢查是否是新車盤的開始（通過編號或特定標記）
                is_new_car = False
                
                # 檢查是否包含編號
                if re.search(r'編號[：:]?\s*s\d+', line) or re.search(r'^s\d{7}', line):
                    is_new_car = True
                
                # 檢查是否包含價格（可能是新車盤）
                if re.search(r'\$\d+\.?\d*萬', line) and not current_block['lines']:
                    is_new_car = True
                
                if is_new_car and current_block['lines']:
                    # 保存之前的區塊
                    car_blocks.append(current_block)
                    current_block = {'start': i, 'lines': [line]}
                else:
                    current_block['lines'].append(line)
            
            # 添加最後一個區塊
            if current_block['lines']:
                car_blocks.append(current_block)
            
            print(f"    🔍 識別到 {len(car_blocks)} 個車盤區塊")
            
            # 處理每個車盤區塊
            for block in car_blocks:
                block_text = ' '.join(block['lines'])
                block_lines = block['lines']
                
                # 提取車盤編號
                car_id = ''
                id_match = re.search(r'編號[：:]?\s*(s\d+)', block_text) or re.search(r'(s\d{7})', block_text)
                if id_match:
                    car_id = id_match.group(1)
                
                # 提取電話（8位數字）
                phone = ''
                phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', block_text)
                if phone_match:
                    phone = phone_match.group(1).replace('-', '').replace(' ', '')
                    if not re.match(r'^\d{8}$', phone):
                        phone = ''
                
                # === 提取車型（改進版）===
                model = ''
                
                # 方法1：找包含品牌的整行，優先選擇較短的行（更可能是車型）
                brand_lines = []
                for line in block_lines:
                    for brand in all_brands:
                        if brand in line:
                            brand_lines.append(line)
                            break
                
                # 從候選行中選擇最適合的車型描述
                if brand_lines:
                    # 優先選擇長度適中（10-50字符）且包含年份或型號的行
                    for line in brand_lines:
                        line = line.strip()
                        # 檢查是否包含年份（20xx 或 19xx）
                        has_year = re.search(r'(20\d{2}|19\d{2})', line)
                        # 檢查是否包含排氣量（如 2000cc, 1.5L）
                        has_cc = re.search(r'(\d{4}cc|\d\.\dL)', line, re.IGNORECASE)
                        
                        if (10 <= len(line) <= 60) and (has_year or has_cc):
                            model = line
                            break
                    
                    # 如果沒找到合適的，選擇最短的品牌行
                    if not model:
                        brand_lines.sort(key=len)
                        for line in brand_lines:
                            if len(line.strip()) >= 5:
                                model = line.strip()
                                break
                
                # 方法2：如果還沒找到，嘗試正則匹配車型格式
                if not model:
                    # 匹配格式：品牌 + 型號 + 年份/其他
                    patterns = [
                        r'([\u4e00-\u9fff]{2,4}\s+[A-Z0-9\-\s]{2,20})',  # 中文品牌 + 型號
                        r'([A-Z][a-zA-Z]{2,15}\s+[A-Z0-9\-\s]{2,15})',  # 英文品牌 + 型號
                        r'((?:奧迪|寶馬|平治|豐田|本田|凌志)[^\n]{5,30})',  # 特定中文品牌
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, block_text)
                        if match:
                            candidate = match.group(1).strip()
                            if 5 <= len(candidate) <= 50:
                                model = candidate
                                break
                
                # 方法3：嘗試從包含排氣量或變速箱信息的行提取
                if not model:
                    for line in block_lines:
                        if re.search(r'(\d{4}cc|汽油|柴油|電動|混能|自動|棍波)', line):
                            for brand in all_brands:
                                if brand in line:
                                    model = line.strip()[:60]
                                    break
                        if model:
                            break
                
                # 清理車型文本
                if model:
                    # 去除多餘空白
                    model = ' '.join(model.split())
                    # 限制長度
                    model = model[:80]
                
                # 如果找到電話或車型，保存記錄
                if phone or model:
                    # 生成來源描述
                    source = f"page_{page_num}_id_{car_id}" if car_id else f"page_{page_num}"
                    
                    # 保存到資料庫
                    if self.db.save_28car(phone or '', '', model or '', source):
                        new_count += 1
                        current = self.db.get_28car_count()
                        
                        # 輸出信息
                        model_str = f" 🚗{model[:40]}" if model else ""
                        phone_str = f" 📞{phone}" if phone else ""
                        id_str = f" [{car_id}]" if car_id else ""
                        
                        print(f"    ✅ [{current}]{id_str}{phone_str}{model_str}")
                        
                        if self.db.get_total_count() >= TARGET_COUNT:
                            break
            
            return new_count
            
        except Exception as e:
            print(f"    ❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def run(self):
        print("\n🚗 啟動 28car.com 爬蟲...")
        
        if not self.init_browser():
            return 0
        
        try:
            page_num = 1
            empty_pages = 0
            
            while self.db.get_total_count() < TARGET_COUNT:
                count = self.scrape_page(page_num)
                
                if count == 0:
                    empty_pages += 1
                    if empty_pages >= 3:
                        break
                else:
                    empty_pages = 0
                
                page_num += 1
                self.random_delay()
                
        finally:
            self.close_browser()
        
        return self.db.get_28car_count()

# ============ Facebook 爬蟲模塊 ============
class FacebookScraper:
    """Facebook 爬蟲器 (使用 undetected-chromedriver)"""
    
    def __init__(self, db):
        self.db = db
        self.driver = None
    
    def init_browser(self):
        if not UC_AVAILABLE:
            print("⚠️ undetected-chromedriver 未安裝，跳過 Facebook")
            return False
        
        try:
            options = uc.ChromeOptions()
            options.add_argument('--user-data-dir=/Users/claw/Library/Application Support/Google/Chrome')
            options.add_argument('--profile-directory=Default')
            options.add_argument('--window-size=1400,900')
            
            self.driver = uc.Chrome(options=options)
            print("✅ Facebook 瀏覽器啟動成功")
            return True
        except Exception as e:
            print(f"❌ Facebook 瀏覽器啟動失敗: {e}")
            return False
    
    def close_browser(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
    
    def random_delay(self):
        time.sleep(random.uniform(3, 7))
    
    def extract_phone(self, text):
        """從文本中提取電話號碼"""
        phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', text)
        if phone_match:
            phone = phone_match.group(1).replace('-', '').replace(' ', '')
            if re.match(r'^\d{8}$', phone):
                return phone
        return None
    
    def extract_email(self, text):
        """從文本中提取電郵"""
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            return email_match.group(0)
        return None
    
    def click_comments_button(self, post):
        """點擊查看評論按鈕"""
        try:
            # 嘗試多種方式找評論按鈕
            comment_buttons = post.find_elements(By.XPATH, './/div[@role="button"]')
            for btn in comment_buttons:
                btn_text = btn.text.lower()
                if 'comment' in btn_text or '評論' in btn_text or '則留言' in btn_text or 'comment' in btn.get_attribute('aria-label', '').lower():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    btn.click()
                    time.sleep(2)
                    return True
        except:
            pass
        return False
    
    def scrape_comments(self, post, keyword, group_url):
        """抓取帖子的評論"""
        comments_data = []
        try:
            # 嘗試展開評論
            self.click_comments_button(post)
            
            # 等待評論加載
            time.sleep(2)
            
            # 找評論元素 - 多種可能的 XPath
            comment_selectors = [
                '//div[@role="article"]//div[contains(@class, "x1y1aw1k")]',  # 評論容器
                '//div[@role="article"]//div[@data-testid="comment"]',
                '//div[@role="article"]//div[contains(@aria-label, "comment")]',
                '//div[contains(@class, "x1n2onr6") and @role="article"]//div[contains(@class, "xdj266r")]',  # 評論文本
            ]
            
            comments = []
            for selector in comment_selectors:
                comments = post.find_elements(By.XPATH, '.' + selector.replace('//', '//'))
                if len(comments) > 0:
                    break
            
            # 如果沒找到，嘗試直接找所有評論文本
            if not comments:
                # 找包含評論文本的元素
                all_divs = post.find_elements(By.XPATH, './/div[contains(@class, "x1iorvi4") or contains(@class, "x9f619")]')
                for div in all_divs:
                    text = div.text
                    if len(text) > 5 and len(text) < 500:  # 評論通常不太長
                        # 檢查是否包含關鍵詞
                        for kw in FB_KEYWORDS:
                            if kw in text:
                                comments.append(div)
                                break
            
            for comment in comments[:10]:  # 限制評論數量
                try:
                    text = comment.text
                    if not text or len(text) < 3:
                        continue
                    
                    # 找評論者名稱
                    user_name = "未知用戶"
                    try:
                        # 嘗試找鏈接作為用戶名
                        user_link = comment.find_element(By.XPATH, './/a[@role="link" or @href]')
                        user_name = user_link.text
                    except:
                        # 嘗試從文本結構推斷用戶名
                        lines = text.split('\n')
                        if len(lines) > 1:
                            user_name = lines[0][:50]  # 第一行通常是用戶名
                    
                    # 提取電話和電郵
                    phone = self.extract_phone(text)
                    email = self.extract_email(text)
                    
                    comments_data.append({
                        'user_name': user_name,
                        'phone': phone,
                        'email': email,
                        'text': text[:200],
                        'keyword': keyword,
                        'is_comment': True
                    })
                    
                except:
                    continue
                    
        except Exception as e:
            print(f"    ⚠️ 抓取評論時出錯: {e}")
        
        return comments_data
    
    def scrape_group(self, group_url):
        try:
            print(f"  📱 訪問群組: {group_url}")
            self.driver.get(group_url)
            self.random_delay()
            
            # 滾動加載帖子
            for _ in range(5):  # 增加滾動次數
                self.driver.execute_script("window.scrollBy(0, 1000)")
                time.sleep(2)
            
            # 找帖子
            posts = self.driver.find_elements(By.XPATH, '//div[@role="article"]')
            print(f"    找到 {len(posts)} 個帖子")
            
            new_count = 0
            for post in posts[:20]:  # 處理前20個
                try:
                    text = post.text
                    if not text:
                        continue
                    
                    # 檢查關鍵詞
                    found_keyword = None
                    for keyword in FB_KEYWORDS:
                        if keyword in text:
                            found_keyword = keyword
                            break
                    
                    if found_keyword:
                        # 找用戶名（帖子作者）
                        try:
                            user_elem = post.find_element(By.XPATH, './/a[@role="link"]')
                            user_name = user_elem.text
                        except:
                            user_name = "未知用戶"
                        
                        # 提取電話號碼和電郵（從帖子）
                        phone = self.extract_phone(text)
                        email = self.extract_email(text)
                        
                        # 保存帖子
                        if self.db.save_fb(user_name, phone, email, text[:150], f"帖子:{found_keyword}", group_url, content_type='post'):
                            new_count += 1
                            phone_str = f" 📞{phone}" if phone else ""
                            email_str = f" 📧{email}" if email else ""
                            print(f"    ✅ 帖子: {user_name}{phone_str}{email_str} - {found_keyword}")
                        
                        # 抓取評論
                        comments = self.scrape_comments(post, found_keyword, group_url)
                        for comment in comments:
                            if self.db.save_fb(
                                comment['user_name'], 
                                comment['phone'], 
                                comment['email'],
                                comment['text'], 
                                f"評論:{comment['keyword']}", 
                                group_url,
                                content_type='comment'
                            ):
                                new_count += 1
                                phone_str = f" 📞{comment['phone']}" if comment['phone'] else ""
                                print(f"      💬 評論: {comment['user_name']}{phone_str}")
                
                except Exception as e:
                    continue
            
            return new_count
            
        except Exception as e:
            print(f"    ❌ 抓取失敗: {e}")
            return 0
    
    def search_keyword(self, keyword):
        """搜索特定關鍵詞的帖子"""
        try:
            search_url = f"https://www.facebook.com/search/posts?q={keyword}"
            print(f"  🔍 搜索: {keyword}")
            self.driver.get(search_url)
            self.random_delay()
            
            # 等待結果加載
            time.sleep(5)
            
            # 滾動加載
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 800)")
                time.sleep(2)
            
            # 找帖子
            posts = self.driver.find_elements(By.XPATH, '//div[@role="article"]')
            print(f"    找到 {len(posts)} 個相關帖子")
            
            new_count = 0
            for post in posts[:10]:
                try:
                    text = post.text
                    if not text:
                        continue
                    
                    # 找用戶名
                    try:
                        user_elem = post.find_element(By.XPATH, './/a[@role="link"]')
                        user_name = user_elem.text
                    except:
                        user_name = "未知用戶"
                    
                    phone = self.extract_phone(text)
                    email = self.extract_email(text)
                    
                    if self.db.save_fb(user_name, phone, email, text[:150], f"搜索:{keyword}", "Facebook搜索", content_type='post'):
                        new_count += 1
                        phone_str = f" 📞{phone}" if phone else ""
                        email_str = f" 📧{email}" if email else ""
                        print(f"    ✅ 搜索結果: {user_name}{phone_str}{email_str}")
                    
                    # 也抓取評論
                    comments = self.scrape_comments(post, keyword, "Facebook搜索")
                    for comment in comments:
                        if self.db.save_fb(
                            comment['user_name'], 
                            comment['phone'], 
                            comment['email'], 
                            comment['text'], 
                            f"搜索評論:{keyword}", 
                            "Facebook搜索",
                            content_type='comment'
                        ):
                            new_count += 1
                            phone_str = f" 📞{comment['phone']}" if comment['phone'] else ""
                            print(f"      💬 評論: {comment['user_name']}{phone_str}")
                    
                except:
                    continue
            
            return new_count
            
        except Exception as e:
            print(f"    ❌ 搜索失敗: {e}")
            return 0
    
    def run(self):
        print("\n📘 啟動 Facebook 爬蟲...")
        
        if not self.init_browser():
            return 0
        
        total_count = 0
        try:
            # 1. 先搜索「港車北上」相關帖子
            for keyword in ['港車北上', '北上車險', '港車北上保險']:
                count = self.search_keyword(keyword)
                total_count += count
                self.random_delay()
                if total_count >= 50:  # 搜索階段限制數量
                    break
            
            # 2. 遍歷群組
            for group in FB_GROUPS:
                if self.db.get_total_count() >= TARGET_COUNT:
                    break
                count = self.scrape_group(group)
                total_count += count
                self.random_delay()
        
        finally:
            self.close_browser()
        
        return total_count

# ============ 主程序 ============
def main():
    print("=" * 70)
    print("🤖 整合爬蟲系統 v2.0")
    print("=" * 70)
    print(f"🎯 目標: {TARGET_COUNT} 條有效數據")
    print(f"📁 輸出: {DATA_DIR}")
    print(f"⏰ 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 初始化數據庫
    db = DatabaseManager()
    
    # 1. 先爬 28car.com
    scraper_28 = Car28Scraper(db)
    count_28 = scraper_28.run()
    
    print(f"\n📊 28car 完成: {count_28} 條")
    
    # 2. 爬 Facebook（確保兩個來源都有數據）
    scraper_fb = FacebookScraper(db)
    count_fb = scraper_fb.run()
    print(f"📊 Facebook 完成: {count_fb} 條")
    
    # 3. 導出 Excel
    total = db.get_total_count()
    print(f"\n{'=' * 70}")
    print(f"📊 總計獲取: {total} 條")
    
    if total > 0:
        count_28_excel, count_fb_excel, count_fb_phone, fb_post_count, fb_comment_count, total_clean = db.export_excel()
        print(f"\n✅ Excel 導出完成:")
        print(f"   📄 28car 資料: {RAW_EXCEL_28CAR}")
        print(f"      - 28car電話: {count_28_excel} 條")
        if count_fb_excel > 0:
            print(f"   📄 Facebook 資料: {RAW_EXCEL_FB}")
            print(f"      - Facebook潛客: {count_fb_excel} 條")
            print(f"      - Facebook有電話: {count_fb_phone} 條")
        print(f"   📄 全部資料: {CLEAN_EXCEL} ({total_clean} 條)")
        print(f"\n📊 來源統計:")
        print(f"   - 28car: {count_28_excel} 條")
        print(f"   - Facebook: {count_fb_excel} 條")
        print(f"     ├─ 帖子: {fb_post_count} 條")
        print(f"     ├─ 評論: {fb_comment_count} 條")
        print(f"     └─ 含電話: {count_fb_phone} 條")
        print(f"   - 合併去重後總計: {total_clean} 個電話")
    
    print(f"{'=' * 70}")
    
    # 檢查是否達標
    if total < TARGET_COUNT:
        print(f"⚠️ 警告: 未達到目標 {TARGET_COUNT} 條，僅獲取 {total} 條")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
