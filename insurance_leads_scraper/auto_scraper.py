#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
28car.com 自動化爬蟲系統 - 自愈架構
自動收集、提取、整理電話號碼到 Excel
"""

import time
import re
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ============ 配置 ============
TARGET_COUNT = 100  # 目標收集數量
DATA_DIR = Path.home() / "Desktop" / "汽車保險潛客數據"
DATA_DIR.mkdir(exist_ok=True)

RAW_EXCEL = DATA_DIR / f"原始數據_{datetime.now().strftime('%Y%m%d')}.xlsx"
CLEAN_EXCEL = DATA_DIR / f"清洗後電話_{datetime.now().strftime('%Y%m%d')}.xlsx"
DB_PATH = DATA_DIR / "auto_scraper.db"

# ============ 自愈機制裝飾器 ============
def retry_on_error(max_retries=3, delay=2):
    """錯誤重試裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"    ⚠️ 錯誤 (嘗試 {i+1}/{max_retries}): {e}")
                    if i < max_retries - 1:
                        time.sleep(delay * (i + 1))
                    else:
                        raise
        return wrapper
    return decorator

# ============ 數據庫管理 ============
class DatabaseManager:
    """自愈數據庫管理"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._ensure_db()
    
    def _ensure_db(self):
        """確保數據庫和表存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE,
                    email TEXT,
                    model TEXT,
                    raw_text TEXT,
                    source_url TEXT,
                    created_at TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"數據庫初始化錯誤: {e}")
            # 嘗試刪除並重建
            if self.db_path.exists():
                self.db_path.unlink()
            self._ensure_db()
    
    @retry_on_error(max_retries=3)
    def save_lead(self, phone, email, model, raw_text, url):
        """保存線索（帶去重）"""
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute('''
                INSERT OR IGNORE INTO leads (phone, email, model, raw_text, source_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (phone, email, model, raw_text, url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            print(f"保存失敗: {e}")
            return False
        finally:
            conn.close()
    
    def get_count(self):
        """獲取當前數量"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM leads")
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def get_all(self):
        """獲取所有數據"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM leads", conn)
        conn.close()
        return df
    
    def reset(self):
        """重置數據庫"""
        if self.db_path.exists():
            self.db_path.unlink()
        self._ensure_db()

# ============ Excel 導出 ============
def export_raw_data(df):
    """導出原始數據（粗糙版）"""
    try:
        df.to_excel(RAW_EXCEL, index=False, sheet_name='原始數據')
        print(f"\n📄 原始數據已導出: {RAW_EXCEL}")
        print(f"   共 {len(df)} 條記錄")
        return True
    except Exception as e:
        print(f"導出原始數據失敗: {e}")
        return False

def export_clean_phones(df):
    """導出清洗後的電話（規範版）"""
    try:
        # 提取8位數電話
        phones = []
        for _, row in df.iterrows():
            phone = str(row.get('phone', ''))
            # 確保是8位數字
            if re.match(r'^\d{8}$', phone):
                phones.append({'電話號碼': phone})
        
        if not phones:
            print("⚠️ 沒有找到有效的8位數電話")
            return False
        
        clean_df = pd.DataFrame(phones)
        clean_df.to_excel(CLEAN_EXCEL, index=False, sheet_name='電話清單')
        
        print(f"\n✅ 清洗後電話已導出: {CLEAN_EXCEL}")
        print(f"   共 {len(clean_df)} 個有效8位數電話")
        return True
    except Exception as e:
        print(f"導出清洗數據失敗: {e}")
        return False

# ============ 爬蟲核心 ============
class ScraperCore:
    """爬蟲核心 - 帶自愈機制"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.browser = None
        self.page = None
    
    def init_browser(self):
        """初始化瀏覽器（帶重試）"""
        for i in range(3):
            try:
                playwright = sync_playwright().start()
                self.browser = playwright.chromium.launch(headless=False)
                self.page = self.browser.new_page(viewport={'width': 1400, 'height': 900})
                print("✅ 瀏覽器啟動成功")
                return True
            except Exception as e:
                print(f"瀏覽器啟動失敗 (嘗試 {i+1}/3): {e}")
                time.sleep(2)
        return False
    
    def close_browser(self):
        """關閉瀏覽器"""
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
    
    @retry_on_error(max_retries=2)
    def scrape_page(self, page_num):
        """爬取單頁（帶錯誤恢復）"""
        url = "https://www.28car.com/sell_lst.php"
        if page_num > 1:
            url += f"?pg={page_num}"
        
        print(f"\n📄 正在爬取第 {page_num} 頁...")
        
        # 訪問頁面
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
        except PlaywrightTimeout:
            print("    頁面加載超時，繼續嘗試...")
            self.page.goto(url, timeout=60000)
        
        time.sleep(10)  # 等待 JS 加載
        
        # 查找內容 frame
        target_frame = None
        for frame in self.page.frames:
            try:
                frame_url = frame.url
                # 查找包含 28car.com 且不是主頁面的 frame
                if '28car.com' in frame_url and 'sell_lst' in frame_url:
                    # 嘗試獲取內容長度
                    text = frame.inner_text('body', timeout=3000)
                    if len(text) > 30000:  # 內容足夠大
                        target_frame = frame
                        print(f"    ✅ 找到內容 frame ({len(text)} 字符)")
                        break
            except Exception as e:
                continue
        
        if not target_frame:
            print("    ⚠️ 未找到內容 frame，嘗試備用方法...")
            # 備用：嘗試所有 frame
            for frame in self.page.frames:
                try:
                    text = frame.inner_text('body', timeout=2000)
                    if len(text) > 40000:
                        target_frame = frame
                        print(f"    ✅ 備用方法找到 frame ({len(text)} 字符)")
                        break
                except:
                    continue
        
        if not target_frame:
            print("    ❌ 確實找不到內容")
            return 0
        
        # 提取數據
        text = target_frame.inner_text('body')
        lines = text.split('\n')
        
        new_count = 0
        for i, line in enumerate(lines):
            # 提取電話
            phone_match = re.search(r'(\d{4}[\s\-]?\d{4})', line)
            if not phone_match:
                continue
            
            phone = phone_match.group(1).replace('-', '').replace(' ', '')
            
            # 確保是8位數
            if not re.match(r'^\d{8}$', phone):
                continue
            
            # 在周圍文本找車型
            context = ' '.join(lines[max(0,i-2):min(len(lines),i+3)])
            model_match = re.search(r'([A-Z][a-zA-Z0-9\s]{2,20}[0-9])', context)
            model = model_match.group(1).strip() if model_match else ''
            
            # 找電郵
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', context)
            email = email_match.group(0) if email_match else ''
            
            # 保存
            if self.db.save_lead(phone, email, model, line[:100], url):
                new_count += 1
                current_total = self.db.get_count()
                print(f"    ✅ [{current_total}] {phone} {model}")
                
                if current_total >= TARGET_COUNT:
                    break
        
        return new_count
    
    def run(self):
        """主運行循環"""
        print("=" * 70)
        print("🚗 28car.com 自動爬蟲系統 - 自愈架構")
        print("=" * 70)
        print(f"🎯 目標: 收集 {TARGET_COUNT} 條有效電話")
        print(f"📁 數據保存: {DATA_DIR}")
        print("=" * 70)
        
        # 重置數據庫（開始新收集）
        self.db.reset()
        
        # 啟動瀏覽器
        if not self.init_browser():
            print("❌ 瀏覽器啟動失敗，退出")
            return False
        
        try:
            page_num = 1
            empty_pages = 0  # 連續空頁計數
            
            while self.db.get_count() < TARGET_COUNT:
                # 爬取頁面
                try:
                    new_count = self.scrape_page(page_num)
                    
                    if new_count == 0:
                        empty_pages += 1
                        if empty_pages >= 3:
                            print("\n⚠️ 連續3頁無數據，可能已到末尾")
                            break
                    else:
                        empty_pages = 0
                    
                except Exception as e:
                    print(f"    ❌ 爬取失敗: {e}")
                    empty_pages += 1
                    if empty_pages >= 3:
                        break
                
                page_num += 1
                time.sleep(3)  # 避免被封
                
                # 顯示進度
                current = self.db.get_count()
                print(f"    📊 當前進度: {current}/{TARGET_COUNT} ({current/TARGET_COUNT*100:.1f}%)")
            
            # 收集完成
            final_count = self.db.get_count()
            print(f"\n{'=' * 70}")
            print(f"✅ 收集完成！共獲取 {final_count} 條記錄")
            
            if final_count > 0:
                # 導出 Excel
                df = self.db.get_all()
                export_raw_data(df)
                export_clean_phones(df)
                print(f"\n🎉 任務完成！Excel 文件已生成")
            else:
                print("\n⚠️ 未收集到任何數據")
            
            print(f"{'=' * 70}")
            return True
            
        finally:
            self.close_browser()

# ============ 主程序 ============
if __name__ == "__main__":
    scraper = ScraperCore()
    scraper.run()
    print("\n✅ 程序已退出")
