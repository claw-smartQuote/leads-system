#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
保險潛在客戶獲取系統 v3.0 - 生產級無頭版本
整合 28car.com 爬蟲 + Facebook 自動化推廣

特性:
- 純無頭模式 (完全後台運行)
- 強制桌面文件歸檔
- 每日 50 條 KPI 保底
- 自動雙 Sheet Excel 導出

作者: AI Assistant
日期: 2026-03-17
版本: 3.0
"""

import os
import re
import sys
import json
import sqlite3
import logging
import argparse
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== 核心配置 ====================

# Facebook 推廣文案
FB_MESSAGE_TEMPLATES = [
    "你好！在群裡看到你對汽車感興趣。我是做汽車保險的，如果有需要報價或諮詢，隨時聯繫我！",
    "Hi！留意到你正在找車相關資訊。我是專業汽車保險代理，歡迎隨時諮詢報價 😊",
    "你好！見你在車群活躍，想問問你的愛車保險是否需要續保或比價？我可以幫手！",
]

FB_KEYWORDS = ["買車", "車險", "二手車", "汽車保險", "換車", "賣車"]

# ==================== 路徑配置（硬編碼桌面路徑）====================

def get_desktop_path() -> Path:
    """獲取用戶桌面絕對路徑"""
    home = Path.home()
    
    # Mac / Linux
    desktop = home / "Desktop"
    if desktop.exists():
        return desktop
    
    # 備用
    desktop = home / "桌面"
    if desktop.exists():
        return desktop
    
    # 萬一都找不到，使用腳本同級目錄
    return Path(__file__).parent


# 🔥🔥🔥 核心數據存儲路徑（硬編碼到桌面）🔥🔥🔥
DESKTOP_DIR = get_desktop_path()
DATA_DIR = DESKTOP_DIR / "汽車保險潛客數據"  # 桌面上的文件夾名稱

# 強制創建目錄（如果不存在會自動創建）
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 各種文件路徑
ARCHIVE_DIR = DATA_DIR           # Excel 文件存放處
DB_PATH = DATA_DIR / "leads_database.db"      # SQLite 去重數據庫
FB_AUTH_FILE = DATA_DIR / "fb_auth.json"      # Facebook 登錄狀態
LOG_FILE = DATA_DIR / "scraper.log"           # 日誌文件

# 添加文件日誌
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

logger.info(f"📂 數據存儲路徑已設置: {DATA_DIR}")

# ==================== KPI 配置 ====================

DEFAULT_KPI_TARGET = 50          # 每日保底 50 條
DEFAULT_MAX_PAGES = 30           # 最大 30 頁
DEFAULT_MAX_RUNTIME = 45 * 60    # 最大 45 分鐘


# ==================== 數據模型 ====================

@dataclass
class CarLead:
    """28Car 車輛銷售線索"""
    source: str = "28car"
    car_model: str = ""
    price: str = ""
    seller_name: str = ""
    phone: str = ""
    post_url: str = ""
    post_id: str = ""
    seller_type: str = ""
    scrape_date: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FacebookLead:
    """Facebook 潛在客戶線索"""
    source: str = "facebook"
    fb_name: str = ""
    fb_id: str = ""
    profile_url: str = ""
    group_name: str = ""
    post_url: str = ""
    keywords_matched: str = ""
    action_taken: str = ""
    message_sent: str = ""
    action_date: str = ""
    status: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ==================== 數據庫管理 ====================

class DatabaseManager:
    """SQLite 數據庫管理器 - 保存在桌面文件夾內"""
    
    def __init__(self, db_path: Path = None):
        # 使用桌面路徑
        self.db_path = str(db_path or DB_PATH)
        
        # 確保目錄存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🗄️  數據庫路徑: {self.db_path}")
        self.init_database()
    
    def init_database(self):
        """初始化數據庫表結構"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 28Car 線索表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS car_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT UNIQUE,
                    phone TEXT UNIQUE,
                    car_model TEXT,
                    price TEXT,
                    seller_name TEXT,
                    post_url TEXT,
                    seller_type TEXT,
                    first_seen_date TEXT,
                    last_seen_date TEXT,
                    scrape_count INTEGER DEFAULT 1
                )
            ''')
            
            # Facebook 線索表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fb_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fb_id TEXT UNIQUE,
                    fb_name TEXT,
                    profile_url TEXT,
                    group_name TEXT,
                    post_url TEXT,
                    keywords_matched TEXT,
                    action_taken TEXT,
                    message_sent TEXT,
                    action_date TEXT,
                    status TEXT,
                    first_contact_date TEXT,
                    last_contact_date TEXT,
                    contact_count INTEGER DEFAULT 1
                )
            ''')
            
            conn.commit()
            logger.info("✅ 數據庫表結構初始化完成")
    
    def is_car_duplicate(self, post_id: str, phone: str) -> bool:
        """檢查 28Car 記錄是否已存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM car_leads WHERE post_id = ? OR phone = ?",
                (post_id, phone)
            )
            return cursor.fetchone() is not None
    
    def insert_car_lead(self, lead: CarLead) -> bool:
        """插入 28Car 線索"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    INSERT INTO car_leads 
                    (post_id, phone, car_model, price, seller_name, post_url, seller_type, first_seen_date, last_seen_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(post_id) DO UPDATE SET
                        last_seen_date = ?,
                        scrape_count = scrape_count + 1
                ''', (
                    lead.post_id, lead.phone, lead.car_model, lead.price,
                    lead.seller_name, lead.post_url, lead.seller_type, today, today, today
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"數據庫錯誤: {e}")
            return False
    
    def is_fb_duplicate(self, fb_id: str) -> bool:
        """檢查 Facebook 用戶是否已聯繫過"""
        if not fb_id:
            return False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM fb_leads WHERE fb_id = ?", (fb_id,))
            return cursor.fetchone() is not None
    
    def insert_fb_lead(self, lead: FacebookLead) -> bool:
        """插入 Facebook 線索"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    INSERT INTO fb_leads 
                    (fb_id, fb_name, profile_url, group_name, post_url, keywords_matched,
                     action_taken, message_sent, action_date, status, first_contact_date, last_contact_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fb_id) DO UPDATE SET
                        last_contact_date = ?,
                        contact_count = contact_count + 1,
                        action_taken = ?,
                        status = ?
                ''', (
                    lead.fb_id, lead.fb_name, lead.profile_url, lead.group_name,
                    lead.post_url, lead.keywords_matched, lead.action_taken,
                    lead.message_sent, lead.action_date, lead.status,
                    today, today, today, lead.action_taken, lead.status
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Facebook 數據庫錯誤: {e}")
            return False


# ==================== Excel 導出管理器 ====================

class ExcelExporter:
    """Excel 導出管理器 - 強制保存到桌面"""
    
    def __init__(self, output_dir: Path = None):
        # 使用桌面路徑
        self.output_dir = output_dir or ARCHIVE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📊 Excel 輸出目錄: {self.output_dir}")
    
    def export(self, car_leads: List[CarLead], fb_leads: List[FacebookLead], 
               filename: str = None) -> str:
        """
        強制導出數據到 Excel（雙 Sheet）
        文件將保存在: ~/Desktop/汽車保險潛客數據/
        """
        # 生成文件名
        if not filename:
            today = datetime.now().strftime('%Y%m%d')
            filename = f"leads_{today}.xlsx"
        
        output_path = self.output_dir / filename
        
        # 🔥 強制寫入 Excel
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Sheet 1: 28Car 線索
                if car_leads:
                    self._write_car_sheet(writer, car_leads)
                    logger.info(f"🚗 寫入 {len(car_leads)} 條 28Car 數據")
                else:
                    # 即使沒有數據也創建空表頭
                    self._write_empty_car_sheet(writer)
                
                # Sheet 2: Facebook 線索
                if fb_leads:
                    self._write_fb_sheet(writer, fb_leads)
                    logger.info(f"📘 寫入 {len(fb_leads)} 條 Facebook 數據")
                else:
                    # 即使沒有數據也創建空表頭
                    self._write_empty_fb_sheet(writer)
            
            logger.info(f"✅ Excel 文件已保存: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"❌ Excel 導出失敗: {e}")
            raise
    
    def _write_car_sheet(self, writer: pd.ExcelWriter, leads: List[CarLead]):
        """寫入 28Car 數據"""
        data = [lead.to_dict() for lead in leads]
        df = pd.DataFrame(data)
        
        # 數據清洗
        df['phone'] = df['phone'].apply(self._clean_phone)
        df['price'] = df['price'].apply(self._clean_price)
        
        # 選擇和重命名列
        columns = ['car_model', 'price', 'seller_name', 'phone', 
                   'seller_type', 'post_url', 'post_id', 'scrape_date']
        df = df[[col for col in columns if col in df.columns]]
        
        column_names = {
            'car_model': '車輛型號',
            'price': '售價',
            'seller_name': '聯絡人',
            'phone': '電話號碼',
            'seller_type': '賣家類型',
            'post_url': '帖子鏈接',
            'post_id': '帖子ID',
            'scrape_date': '抓取日期'
        }
        df.rename(columns=column_names, inplace=True)
        
        df.to_excel(writer, index=False, sheet_name='28Car_Leads')
    
    def _write_fb_sheet(self, writer: pd.ExcelWriter, leads: List[FacebookLead]):
        """寫入 Facebook 數據"""
        data = [lead.to_dict() for lead in leads]
        df = pd.DataFrame(data)
        
        columns = ['fb_name', 'fb_id', 'profile_url', 'group_name', 'post_url',
                   'keywords_matched', 'action_taken', 'message_sent', 'action_date', 'status']
        df = df[[col for col in columns if col in df.columns]]
        
        column_names = {
            'fb_name': 'FB姓名',
            'fb_id': 'FB_ID',
            'profile_url': '個人主頁',
            'group_name': '群組名稱',
            'post_url': '帖子鏈接',
            'keywords_matched': '匹配關鍵詞',
            'action_taken': '執行動作',
            'message_sent': '發送消息',
            'action_date': '操作日期',
            'status': '狀態'
        }
        df.rename(columns=column_names, inplace=True)
        
        df.to_excel(writer, index=False, sheet_name='Facebook_Leads')
    
    def _write_empty_car_sheet(self, writer: pd.ExcelWriter):
        """創建空的 28Car 表頭"""
        df = pd.DataFrame(columns=['車輛型號', '售價', '聯絡人', '電話號碼', 
                                   '賣家類型', '帖子鏈接', '帖子ID', '抓取日期'])
        df.to_excel(writer, index=False, sheet_name='28Car_Leads')
    
    def _write_empty_fb_sheet(self, writer: pd.ExcelWriter):
        """創建空的 Facebook 表頭"""
        df = pd.DataFrame(columns=['FB姓名', 'FB_ID', '個人主頁', '群組名稱', '帖子鏈接',
                                   '匹配關鍵詞', '執行動作', '發送消息', '操作日期', '狀態'])
        df.to_excel(writer, index=False, sheet_name='Facebook_Leads')
    
    def _clean_phone(self, phone: str) -> str:
        if not phone:
            return ''
        cleaned = re.sub(r'\D', '', phone)
        if len(cleaned) == 8:
            return f"{cleaned[:4]} {cleaned[4:]}"
        return cleaned
    
    def _clean_price(self, price: str) -> str:
        if not price:
            return ''
        match = re.search(r'HK\$[\d,]+', price)
        return match.group(0) if match else price


# ==================== KPI 控制器 ====================

class KPICONTROLLER:
    """KPI 保底邏輯控制器"""
    
    def __init__(self, target: int = DEFAULT_KPI_TARGET, 
                 max_pages: int = DEFAULT_MAX_PAGES,
                 max_runtime: int = DEFAULT_MAX_RUNTIME):
        self.target = target
        self.max_pages = max_pages
        self.max_runtime = max_runtime
        self.new_leads_count = 0
        self.pages_processed = 0
        self.groups_processed = 0
        self.start_time = None
        self.should_stop = False
    
    def start(self):
        """開始計時"""
        self.start_time = datetime.now()
        logger.info(f"🎯 KPI 目標: 至少 {self.target} 條新線索")
        logger.info(f"⏱️  限制: 最大 {self.max_pages} 頁 / {self.max_runtime//60} 分鐘")
    
    def add_lead(self, count: int = 1):
        """添加新線索計數"""
        self.new_leads_count += count
        logger.info(f"📊 當前進度: {self.new_leads_count}/{self.target} 條 ({self.new_leads_count/self.target*100:.1f}%)")
    
    def increment_page(self):
        self.pages_processed += 1
    
    def increment_group(self):
        self.groups_processed += 1
    
    def check_should_continue(self) -> bool:
        """檢查是否應該繼續抓取"""
        # 達到 KPI
        if self.new_leads_count >= self.target:
            logger.info(f"✅ KPI 達成！已獲取 {self.new_leads_count} 條新線索")
            return False
        
        # 超過頁數限制
        if self.pages_processed >= self.max_pages:
            logger.warning(f"⚠️ 已達最大頁數限制 ({self.max_pages})")
            self.should_stop = True
            return False
        
        # 超過群組限制
        if self.groups_processed >= self.max_pages:
            logger.warning(f"⚠️ 已達最大群組限制")
            self.should_stop = True
            return False
        
        # 超過時間限制
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed >= self.max_runtime:
                logger.warning(f"⏰ 已達最大運行時間 ({self.max_runtime//60} 分鐘)")
                self.should_stop = True
                return False
        
        return True
    
    def get_status(self) -> dict:
        """獲取當前狀態"""
        elapsed = 0
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            'new_leads': self.new_leads_count,
            'target': self.target,
            'pages_processed': self.pages_processed,
            'groups_processed': self.groups_processed,
            'elapsed_seconds': int(elapsed),
            'elapsed_minutes': round(elapsed / 60, 1),
            'should_stop': self.should_stop
        }


# ==================== 瀏覽器基類（純無頭模式）====================

class BaseScraper(ABC):
    """爬蟲基類 - 強制無頭模式"""
    
    def __init__(self, kpi_controller: KPICONTROLLER = None):
        # 強制無頭模式
        self.headless = True
        self.kpi = kpi_controller
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.db = DatabaseManager()
        self.playwright = None
    
    def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """隨機延遲"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def human_like_scroll(self, page: Page, times: int = 3):
        """模擬人類滾動行為"""
        for _ in range(times):
            scroll_amount = random.randint(300, 800)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            self.random_delay(0.5, 1.5)
    
    def start_browser(self, storage_state: str = None, headless: bool = False):
        """
        啟動瀏覽器
        注意: 28car.com 需要 headless=False 才能繞過 Cloudflare
        """
        mode = "無頭（後台）" if headless else "有頭（可見）"
        logger.info(f"🌐 啟動{mode}瀏覽器...")
        self.playwright = sync_playwright().start()
        
        # 反檢測參數
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]
        
        # 啟動瀏覽器
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # 創建上下文
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'zh-HK',
            'timezone_id': 'Asia/Hong_Kong',
        }
        
        if storage_state and Path(storage_state).exists():
            logger.info(f"📂 加載登錄狀態: {storage_state}")
            context_options['storage_state'] = storage_state
        
        self.context = self.browser.new_context(**context_options)
        
        # 添加反檢測腳本
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)
        
        logger.info(f"✅ 瀏覽器啟動成功")
    
    def close_browser(self):
        """關閉瀏覽器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("🔒 瀏覽器已關閉")
    
    def save_storage_state(self, path: str):
        """保存瀏覽器狀態"""
        if self.context:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.context.storage_state(path=path)
            logger.info(f"💾 登錄狀態已保存: {path}")
    
    @abstractmethod
    def run(self) -> List:
        pass


# ==================== 28Car 爬蟲模塊 ====================

class Car28Scraper(BaseScraper):
    """28car.com 爬蟲 - 純無頭 + KPI"""
    
    BASE_URL = "https://www.28car.com"
    LIST_URL = "https://www.28car.com/sell_lst.php"
    
    def run(self) -> List[CarLead]:
        """運行 28Car 爬蟲 - 帶 KPI 保底"""
        logger.info("🚗 開始 28Car 爬蟲（有頭模式 - 會彈出瀏覽器）")
        
        if self.kpi:
            self.kpi.start()
        
        # 28car 需要 headless=False 才能繞過 Cloudflare
        self.start_browser(headless=False)
        leads = []
        
        try:
            page_num = 1
            
            while True:
                # 檢查 KPI
                if self.kpi and not self.kpi.check_should_continue():
                    if self.kpi.should_stop:
                        logger.warning(f"⚠️ 達到安全限制，提前結束。已獲取 {len(leads)} 條")
                    break
                
                logger.info(f"\n📄 處理第 {page_num} 頁...")
                
                # 抓取當前頁
                cars = self._scrape_list_page(page_num)
                
                if not cars:
                    logger.warning(f"第 {page_num} 頁無數據，嘗試下一頁...")
                    page_num += 1
                    if self.kpi:
                        self.kpi.increment_page()
                    self.random_delay(2, 4)
                    continue
                
                # 處理每輛車
                for car in cars:
                    try:
                        post_id = car.get('post_id', '')
                        
                        # 優先使用列表頁直接獲取的電話
                        phone = car.get('phone', '')
                        seller_name = ''
                        seller_type = '私人'  # 默認為私人賣家
                        
                        # 如果列表頁沒有電話，才進入詳情頁
                        if not phone and car.get('detail_url'):
                            detail = self._scrape_detail_page(car.get('detail_url'))
                            phone = detail.get('phone', '')
                            seller_name = detail.get('seller_name', '')
                            seller_type = detail.get('seller_type', '私人')
                        
                        # 跳過無電話的記錄
                        if not phone:
                            continue
                        
                        # 去重檢查
                        if self.db.is_car_duplicate(post_id, phone):
                            continue
                        
                        # 創建線索
                        lead = CarLead(
                            car_model=car.get('model', ''),
                            price=car.get('price', ''),
                            seller_name=seller_name,
                            phone=phone,
                            post_url=car.get('detail_url', ''),
                            post_id=post_id,
                            seller_type=seller_type,
                            scrape_date=datetime.now().strftime('%Y-%m-%d')
                        )
                        leads.append(lead)
                        self.db.insert_car_lead(lead)
                        
                        if self.kpi:
                            self.kpi.add_lead(1)
                        
                        logger.info(f"✅ 新線索: {lead.car_model} - {lead.phone}")
                    
                    except Exception as e:
                        logger.error(f"處理車輛時出錯: {e}")
                        continue
                
                logger.info(f"📊 第 {page_num} 頁完成")
                
                if self.kpi:
                    self.kpi.increment_page()
                
                page_num += 1
                self.random_delay(3, 5)
        
        finally:
            self.close_browser()
        
        # 統計
        if self.kpi:
            status = self.kpi.get_status()
            logger.info(f"\n📈 28Car 完成 - {len(leads)} 條 | {status['pages_processed']} 頁 | {status['elapsed_minutes']} 分鐘")
        
        return leads
    
    def _get_content_frame(self):
        """獲取包含實際內容的 iframe"""
        logger.info("  等待 iframe 載入...")
        
        # 等待 iframe 載入（最多 15 秒）
        for i in range(15):
            frames = self.page.frames
            
            for frame in frames:
                url = frame.url
                # 找到包含 sell_lst 且 URL 較長的 frame（實際內容 frame）
                if 'sell_lst' in url and '28car.com' in url and len(url) > 50:
                    try:
                        html = frame.content()
                        if len(html) > 100000:  # 確認有實際內容
                            logger.info(f"  ✅ 找到內容 iframe ({len(html)} bytes)")
                            return frame
                    except:
                        pass
            
            time.sleep(1)
        
        logger.warning("  ⚠️ 未找到內容 iframe")
        return None
    
    def _scrape_list_page(self, page_num: int) -> List[Dict]:
        """抓取列表頁 - 從 iframe 獲取數據"""
        url = f"{self.LIST_URL}?ct=0&cty=0&make=0&sort=insdate_d"
        if page_num > 1:
            url += f"&pg={page_num}"
        
        try:
            logger.info(f"  載入頁面: {url}")
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            self.random_delay(3, 5)
            
            # 獲取內容 iframe
            logger.info("  等待 iframe 載入...")
            content_frame = self._get_content_frame()
            
            if not content_frame:
                logger.warning("  未找到內容 iframe，重試...")
                return []
            
            logger.info(f"  ✅ 找到 iframe: {content_frame.url[:50]}")
            self.random_delay(2, 3)
            
            # 從 iframe 獲取 HTML
            html = content_frame.content()
            logger.info(f"  HTML 長度: {len(html)}")
            
            cars = []
            
            # 解析表格行
            # 從截圖看，數據在表格中，使用正則表達式提取
            # 每行包含: 車型、價格、聯絡信息等
            
            # 查找所有車輛行（通過 h_vid 識別）
            # 模式: onclick="goDsp(...)" 或包含 sell_dsp.php?h_vid= 的鏈接
            vid_matches = re.findall(r'h_vid[=\"\'](\d+)', html)
            logger.info(f"  找到 {len(vid_matches)} 個車輛 ID")
            
            # 嘗試通過 Playwright 選擇器獲取行
            try:
                rows = content_frame.query_selector_all('tr')
                logger.info(f"  找到 {len(rows)} 個表格行")
                
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) < 5:
                            continue
                        
                        # 獲取車型（第二列）
                        model_cell = cells[1]
                        model_link = model_cell.query_selector('a')
                        car_model = ''
                        detail_url = ''
                        
                        if model_link:
                            car_model = model_link.inner_text().strip()
                            detail_url = model_link.get_attribute('href') or ''
                        else:
                            car_model = model_cell.inner_text().strip()
                        
                        if not car_model or len(car_model) < 3 or car_model.startswith('$'):
                            continue
                        
                        # 獲取描述（第三列）- 可能包含電話
                        desc_cell = cells[2]
                        desc_text = desc_cell.inner_text().strip() if desc_cell else ''
                        
                        # 獲取價格（第四或第五列）
                        price_text = ''
                        for idx in [3, 4]:
                            if idx < len(cells):
                                price_cell = cells[idx]
                                text = price_cell.inner_text().strip()
                                if '$' in text or 'HK' in text:
                                    price_text = text
                                    break
                        
                        # 提取電話（從描述中）
                        phone_match = re.search(r'(?:電話|Tel)[:\s]*(\d{4}[\s-]?\d{4})', desc_text)
                        phone = phone_match.group(1).replace('-', '').replace(' ', '') if phone_match else ''
                        
                        # 提取車輛 ID
                        post_id = ''
                        if detail_url:
                            vid_match = re.search(r'h_vid=(\d+)', detail_url)
                            post_id = vid_match.group(1) if vid_match else ''
                        
                        # 構建完整 URL
                        if detail_url and not detail_url.startswith('http'):
                            detail_url = 'https://www.28car.com/' + detail_url.lstrip('/')
                        
                        cars.append({
                            'model': car_model,
                            'price': price_text,
                            'desc': desc_text,
                            'phone': phone,
                            'detail_url': detail_url,
                            'post_id': post_id
                        })
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                logger.error(f"  選擇器提取失敗: {e}")
            
            logger.info(f"  ✅ 提取到 {len(cars)} 輛車")
            return cars
            
        except Exception as e:
            logger.error(f"列表頁抓取失敗: {e}")
            return []
    
    def _scrape_detail_page(self, url: str) -> Dict:
        """抓取詳情頁"""
        info = {'seller_name': '', 'phone': '', 'seller_type': '未知'}
        
        if not url:
            return info
        
        try:
            detail_page = self.browser.new_page()
            detail_page.goto(url, wait_until='domcontentloaded', timeout=15000)
            self.random_delay(1, 2)
            
            page_text = detail_page.inner_text('body')
            
            dealer_keywords = ['車行', '汽車貿易', 'MOTOR', 'TRADING', 'SHOWROOM']
            info['seller_type'] = '車行' if any(k in page_text.upper() for k in dealer_keywords) else '私人'
            
            phone_matches = re.findall(r'\d{4}[\s-]?\d{4}', page_text.replace(' ', '').replace('-', ''))
            if phone_matches:
                info['phone'] = phone_matches[0]
            
            name_match = re.search(r'聯絡[人:]?\s*([\u4e00-\u9fa5]{2,4}|[A-Za-z\s]{2,20})', page_text)
            if name_match:
                info['seller_name'] = name_match.group(1).strip()
            
            detail_page.close()
        except Exception as e:
            logger.warning(f"詳情頁抓取失敗: {e}")
        
        return info
    
    def _is_private_seller(self, car: Dict, detail: Dict) -> bool:
        """判斷是否為私人賣家"""
        if detail.get('seller_type') == '車行':
            return False
        dealer_keywords = ['車行', '貿易', 'TRADING', 'SHOWROOM']
        return not any(k in car.get('model', '').upper() for k in dealer_keywords)


# ==================== Facebook 自動化模塊 ====================

class FacebookScraper(BaseScraper):
    """Facebook 自動化 - 純無頭 + KPI"""
    
    FB_URL = "https://www.facebook.com"
    
    def __init__(self, kpi_controller: KPICONTROLLER = None,
                 keywords: List[str] = None, groups: List[str] = None):
        super().__init__(kpi_controller)
        self.keywords = keywords or FB_KEYWORDS
        self.target_groups = groups or []
        self.leads: List[FacebookLead] = []
    
    def run(self) -> List[FacebookLead]:
        """運行 Facebook 推廣 - 帶 KPI 保底"""
        logger.info("📘 開始 Facebook 推廣（無頭模式）")
        
        if self.kpi:
            self.kpi.start()
        
        # 檢查登錄狀態
        has_auth = FB_AUTH_FILE.exists()
        self.start_browser(storage_state=str(FB_AUTH_FILE) if has_auth else None)
        
        try:
            if not has_auth:
                logger.error("❌ 未找到 Facebook 登錄狀態")
                logger.error("   請先運行一次帶瀏覽器的版本進行登錄，或手動創建 fb_auth.json")
                return []
            
            logger.info("✅ 已加載 Facebook 登錄狀態")
            
            if not self._verify_login():
                logger.error("❌ Facebook 登錄狀態已失效，需要重新登錄")
                return []
            
            # KPI 主循環
            if self.target_groups:
                for group_idx, group_url in enumerate(self.target_groups):
                    if self.kpi and not self.kpi.check_should_continue():
                        if self.kpi.should_stop:
                            logger.warning(f"⚠️ 達到安全限制，提前結束")
                        break
                    
                    logger.info(f"\n🌐 處理群組 {group_idx + 1}/{len(self.target_groups)}")
                    self._process_group(group_url)
                    
                    if self.kpi:
                        self.kpi.increment_group()
                    
                    self.random_delay(5, 10)
            else:
                logger.warning("⚠️ 未指定目標群組")
        
        finally:
            self.close_browser()
        
        # 統計
        if self.kpi:
            status = self.kpi.get_status()
            logger.info(f"\n📈 Facebook 完成 - {len(self.leads)} 條 | {status['groups_processed']} 群組 | {status['elapsed_minutes']} 分鐘")
        
        return self.leads
    
    def _verify_login(self) -> bool:
        """驗證登錄狀態"""
        try:
            self.page.goto(self.FB_URL)
            self.random_delay(2, 3)
            nav = self.page.query_selector('[aria-label="Facebook"]') or \
                  self.page.query_selector('[role="navigation"]')
            return nav is not None
        except:
            return False
    
    def _process_group(self, group_url: str):
        """處理單個群組"""
        try:
            self.page.goto(group_url)
            self.random_delay(3, 5)
            self.human_like_scroll(self.page, times=5)
            
            group_name = self._get_group_name()
            posts = self._search_posts()
            
            for post in posts:
                if self.kpi and not self.kpi.check_should_continue():
                    break
                
                try:
                    self._process_post(post, group_name, group_url)
                except Exception as e:
                    logger.error(f"處理帖子時出錯: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"處理群組失敗: {e}")
    
    def _get_group_name(self) -> str:
        """獲取群組名稱"""
        try:
            title = self.page.title()
            return title.replace(' | Facebook', '').strip()
        except:
            return "Unknown"
    
    def _search_posts(self) -> List:
        """搜索帖子"""
        try:
            post_selectors = [
                '[role="article"]',
                '[data-ad-preview="message"]',
                'div[aria-describedby]'
            ]
            
            for selector in post_selectors:
                posts = self.page.query_selector_all(selector)
                if posts:
                    return posts[:10]
            
            return []
        except:
            return []
    
    def _process_post(self, post, group_name: str, group_url: str):
        """處理單個帖子"""
        try:
            post_text = post.inner_text().lower()
        except:
            return
        
        # 關鍵詞匹配
        matched_keywords = [k for k in self.keywords if k.lower() in post_text]
        if not matched_keywords:
            return
        
        # 提取用戶信息
        user_info = self._extract_user_info(post)
        if not user_info.get('fb_id'):
            return
        
        # 去重檢查
        if self.db.is_fb_duplicate(user_info['fb_id']):
            logger.debug(f"跳過已聯繫用戶: {user_info['fb_name']}")
            return
        
        # 執行互動
        actions = self._interact_with_user(post, user_info)
        
        # 創建線索
        lead = FacebookLead(
            fb_name=user_info.get('fb_name', ''),
            fb_id=user_info.get('fb_id', ''),
            profile_url=user_info.get('profile_url', ''),
            group_name=group_name,
            post_url=group_url,
            keywords_matched=', '.join(matched_keywords),
            action_taken=actions.get('action', ''),
            message_sent=actions.get('message', ''),
            action_date=datetime.now().strftime('%Y-%m-%d'),
            status=actions.get('status', 'unknown')
        )
        
        self.leads.append(lead)
        self.db.insert_fb_lead(lead)
        
        # 更新 KPI
        if self.kpi:
            self.kpi.add_lead(1)
        
        logger.info(f"✅ Facebook 新線索: {lead.fb_name}")
        
        # 反檢測延遲
        self.random_delay(5, 10)
    
    def _extract_user_info(self, post) -> Dict:
        """提取用戶信息"""
        info = {'fb_id': '', 'fb_name': '', 'profile_url': ''}
        
        try:
            user_link = post.query_selector('a[href*="/groups/"]') or \
                       post.query_selector('a[role="link"]')
            
            if user_link:
                href = user_link.get_attribute('href') or ''
                info['profile_url'] = href
                info['fb_name'] = user_link.inner_text().strip() or 'Unknown'
                
                uid_match = re.search(r'user_id=(\d+)', href) or re.search(r'/(\d+)/', href)
                info['fb_id'] = uid_match.group(1) if uid_match else href
        except:
            pass
        
        return info
    
    def _interact_with_user(self, post, user_info: Dict) -> Dict:
        """與用戶互動"""
        result = {'action': '', 'message': '', 'status': 'failed'}
        
        try:
            user_link = post.query_selector('a[role="link"]')
            if user_link:
                user_link.click()
                self.random_delay(3, 5)
                
                # 加好友
                add_btn = self.page.query_selector('text=Add Friend') or \
                         self.page.query_selector('text=加為好友')
                if add_btn:
                    add_btn.click()
                    result['action'] = 'friend_request'
                    result['status'] = 'success'
                    self.random_delay(2, 4)
                
                # 發消息
                msg_btn = self.page.query_selector('text=Message') or \
                         self.page.query_selector('text=發消息')
                if msg_btn:
                    msg_btn.click()
                    self.random_delay(3, 5)
                    
                    message = random.choice(FB_MESSAGE_TEMPLATES)
                    input_box = self.page.query_selector('[role="textbox"]') or \
                               self.page.query_selector('div[contenteditable="true"]')
                    
                    if input_box:
                        input_box.fill(message)
                        self.random_delay(2, 3)
                        
                        send_btn = self.page.query_selector('[aria-label="Send"]') or \
                                  self.page.query_selector('text=發送')
                        if send_btn:
                            send_btn.click()
                            result['action'] += '_message_sent' if result['action'] else 'message_sent'
                            result['message'] = message
                            result['status'] = 'success'
                            self.random_delay(2, 3)
                
                self.page.go_back()
                self.random_delay(2, 3)
        
        except Exception as e:
            logger.error(f"互動失敗: {e}")
        
        return result


# ==================== 首次登錄工具（需要瀏覽器版本）====================

def create_fb_auth():
    """
    首次登錄工具 - 用於創建 Facebook 登錄狀態
    這個函數會彈出瀏覽器讓你手動登錄，然後保存狀態
    """
    print("\n" + "="*60)
    print("🔐 Facebook 首次登錄工具")
    print("="*60)
    print("這個工具會彈出瀏覽器讓你登錄 Facebook")
    print("登錄成功後，登錄狀態會自動保存到桌面文件夾")
    print("="*60 + "\n")
    
    # 確保目錄存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    playwright = sync_playwright().start()
    
    # 使用有界面模式
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = context.new_page()
    
    page.goto("https://www.facebook.com")
    
    input("\n👉 請在瀏覽器中完成 Facebook 登錄，然後按 Enter 繼續...")
    
    # 保存登錄狀態
    context.storage_state(path=str(FB_AUTH_FILE))
    
    browser.close()
    playwright.stop()
    
    print(f"\n✅ 登錄狀態已保存到: {FB_AUTH_FILE}")
    print("現在可以運行無頭模式的爬蟲了！\n")


# ==================== 主程序入口 ====================

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='保險潛在客戶獲取系統 v3.0（無頭模式）')
    parser.add_argument('--task', choices=['28car', 'facebook', 'all'], 
                       default='28car', help='選擇任務類型')
    parser.add_argument('--create-fb-auth', action='store_true',
                       help='創建 Facebook 登錄狀態（會彈出瀏覽器）')
    parser.add_argument('--kpi-target', type=int, default=DEFAULT_KPI_TARGET,
                       help=f'KPI 保底目標（默認 {DEFAULT_KPI_TARGET}）')
    parser.add_argument('--max-pages', type=int, default=DEFAULT_MAX_PAGES,
                       help=f'最大頁數限制（默認 {DEFAULT_MAX_PAGES}）')
    parser.add_argument('--max-time', type=int, default=DEFAULT_MAX_RUNTIME//60,
                       help=f'最大運行時間分鐘（默認 {DEFAULT_MAX_RUNTIME//60}）')
    args = parser.parse_args()
    
    # 首次登錄工具
    if args.create_fb_auth:
        create_fb_auth()
        return
    
    # 顯示配置信息
    print(f"\n" + "="*60)
    print("🚀 保險潛在客戶獲取系統 v3.0")
    print("="*60)
    print(f"📂 數據存儲: {DATA_DIR}")
    print(f"🎯 KPI 目標: {args.kpi_target} 條新線索")
    print(f"⏱️  限制: {args.max_pages} 頁 / {args.max_time} 分鐘")
    print(f"🔧 任務: {args.task}")
    print(f"🌐 模式: 純無頭（後台運行）")
    print("="*60 + "\n")
    
    # 創建 KPI 控制器
    kpi = KPICONTROLLER(
        target=args.kpi_target,
        max_pages=args.max_pages,
        max_runtime=args.max_time * 60
    )
    
    car_leads = []
    fb_leads = []
    
    try:
        # 28Car 任務
        if args.task in ['28car', 'all']:
            scraper = Car28Scraper(kpi_controller=kpi)
            car_leads = scraper.run()
        
        # Facebook 任務
        if args.task in ['facebook', 'all']:
            # 檢查登錄狀態
            if not FB_AUTH_FILE.exists():
                print("\n❌ 錯誤: 未找到 Facebook 登錄狀態")
                print(f"   請先運行: python3 main.py --create-fb-auth")
                print("   完成登錄後再運行無頭模式\n")
                return
            
            fb_scraper = FacebookScraper(
                kpi_controller=kpi,
                groups=[]  # 在這裡添加目標群組 URL
            )
            fb_leads = fb_scraper.run()
        
        # 強制導出 Excel
        print(f"\n📊 正在導出 Excel...")
        exporter = ExcelExporter()
        output_file = exporter.export(car_leads, fb_leads)
        
        if output_file:
            print(f"\n" + "="*60)
            print("✅ 任務完成！")
            print("="*60)
            print(f"📊 Excel 文件: {output_file}")
            print(f"🚗 28Car: {len(car_leads)} 條")
            print(f"📘 Facebook: {len(fb_leads)} 條")
            print(f"🗄️  數據庫: {DB_PATH}")
            print("="*60 + "\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 用戶中斷操作")
        # 中斷時也嘗試保存已抓取數據
        if car_leads or fb_leads:
            print("正在保存已抓取數據...")
            exporter = ExcelExporter()
            exporter.export(car_leads, fb_leads)
    except Exception as e:
        logger.error(f"程序執行出錯: {e}")
        raise


if __name__ == "__main__":
    main()
