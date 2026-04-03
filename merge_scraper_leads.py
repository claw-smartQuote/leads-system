#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬蟲潛客整合腳本 (已優化版本)
整合 28car + Facebook 爬蟲結果，去重並生成總滙

修復內容:
1. 添加 SQLite 超時設置和重試機制
2. 添加詳細日誌記錄
3. 優化數據庫連接處理
"""

import pandas as pd
import sqlite3
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import shutil

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 設定
WORKSPACE = Path('/Users/claw/.openclaw/workspace')
OUTPUT_DIR = WORKSPACE / '爬蟲潛客總滙'
BACKUP_DIR = OUTPUT_DIR / '備份'
LOG_DIR = WORKSPACE / 'logs'

# 數據庫路徑
CAR28_DB = WORKSPACE / 'car28_scraper.db'
FB_DB = WORKSPACE / 'fb_leads_final.db'

# SQLite 連接配置
SQLITE_TIMEOUT = 30  # 秒
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒


def ensure_dirs():
    """確保目錄存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"目錄檢查完成: {OUTPUT_DIR}")


def connect_with_retry(db_path: Path, max_retries: int = MAX_RETRIES) -> Optional[sqlite3.Connection]:
    """
    帶重試機制的 SQLite 連接
    
    Args:
        db_path: 數據庫文件路徑
        max_retries: 最大重試次數
        
    Returns:
        sqlite3.Connection 或 None
    """
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(
                str(db_path),
                timeout=SQLITE_TIMEOUT,
                isolation_level=None  # 自動提交模式，避免鎖表
            )
            # 設置 WAL 模式以提高並發性能
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")  # 30秒超時
            logger.info(f"成功連接數據庫: {db_path}")
            return conn
        except sqlite3.Error as e:
            logger.warning(f"數據庫連接失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # 指數退避
            else:
                logger.error(f"數據庫連接最終失敗: {db_path}")
                return None
    return None


def execute_query_with_retry(conn: sqlite3.Connection, query: str, 
                              max_retries: int = MAX_RETRIES) -> Optional[pd.DataFrame]:
    """
    帶重試機制的 SQL 查詢執行
    
    Args:
        conn: 數據庫連接
        query: SQL 查詢語句
        max_retries: 最大重試次數
        
    Returns:
        pd.DataFrame 或 None
    """
    for attempt in range(max_retries):
        try:
            df = pd.read_sql_query(query, conn)
            return df
        except Exception as e:
            logger.warning(f"查詢執行失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"查詢執行最終失敗: {query[:100]}...")
                return None
    return None


def export_28car_to_excel() -> Optional[pd.DataFrame]:
    """從 28car 數據庫導出到 Excel"""
    if not CAR28_DB.exists():
        logger.warning(f"28car 數據庫不存在: {CAR28_DB}")
        return None
    
    conn = connect_with_retry(CAR28_DB)
    if not conn:
        return None
    
    try:
        query = "SELECT * FROM car28_leads ORDER BY created_at DESC"
        df = execute_query_with_retry(conn, query)
        
        if df is None or df.empty:
            logger.warning("28car 沒有數據")
            return None
        
        # 重命名欄位以統一格式
        df = df.rename(columns={
            'phone': '電話',
            'email': '電郵',
            'model': '車型',
            'description': '描述',
            'source': '來源',
            'page': '頁數',
            'created_at': '抓取時間'
        })
        
        # 添加來源標記
        df['平台'] = '28car'
        
        logger.info(f"✅ 28car: {len(df)} 筆")
        return df
    except Exception as e:
        logger.error(f"導出 28car 數據失敗: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass


def export_fb_to_excel() -> Optional[pd.DataFrame]:
    """從 Facebook 數據庫導出到 Excel"""
    if not FB_DB.exists():
        logger.warning(f"Facebook 數據庫不存在: {FB_DB}")
        return None
    
    conn = connect_with_retry(FB_DB)
    if not conn:
        return None
    
    try:
        query = "SELECT * FROM fb_leads ORDER BY scraped_at DESC"
        df = execute_query_with_retry(conn, query)
        
        if df is None or df.empty:
            logger.warning("Facebook 沒有數據")
            return None
        
        # 重命名欄位以統一格式
        df = df.rename(columns={
            'commenter_name': '名稱',
            'commenter_profile_url': 'FB連結',
            'comment_text': '留言內容',
            'post_url': '貼文連結',
            'scraped_at': '抓取時間'
        })
        
        # 添加來源標記
        df['平台'] = 'Facebook'
        
        # 嘗試從留言中提取電話號碼
        df['電話'] = df['留言內容'].apply(extract_phone_from_text)
        
        logger.info(f"✅ Facebook: {len(df)} 筆")
        return df
    except Exception as e:
        logger.error(f"導出 Facebook 數據失敗: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass


def extract_phone_from_text(text: Any) -> Optional[str]:
    """從文字中提取香港電話號碼"""
    if pd.isna(text):
        return None
    
    import re
    # 香港電話號碼模式：5xxx xxxx, 6xxx xxxx, 9xxx xxxx, 8xxx xxxx
    pattern = r'(?:\+?852[-\s]?)?(?:5|6|8|9)\d{3}[-\s]?\d{4}'
    matches = re.findall(pattern, str(text))
    
    if matches:
        # 清理格式
        phone = re.sub(r'\D', '', matches[0])
        if phone.startswith('852'):
            phone = phone[3:]
        return phone
    return None


def merge_and_deduplicate(df28: Optional[pd.DataFrame], 
                          df_fb: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """合併並去重"""
    all_data = []
    
    if df28 is not None and not df28.empty:
        all_data.append(df28)
    if df_fb is not None and not df_fb.empty:
        all_data.append(df_fb)
    
    if not all_data:
        logger.warning("⚠️ 沒有可整合的數據")
        return None
    
    # 合併
    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"\n📊 合併完成: {len(combined)} 筆")
    
    # 去重：根據電話號碼
    if '電話' in combined.columns:
        before = len(combined)
        # 先按抓取時間排序（最新的在後面）
        if '抓取時間' in combined.columns:
            combined['抓取時間'] = pd.to_datetime(combined['抓取時間'], errors='coerce')
            combined = combined.sort_values('抓取時間')
        
        # 去重，保留最後一條（最新的）
        combined = combined.drop_duplicates(subset=['電話'], keep='last')
        after = len(combined)
        removed = before - after
        logger.info(f"🔍 去重完成: 刪除 {removed} 筆重複，剩餘 {after} 筆")
    
    return combined


def save_results(df: pd.DataFrame) -> Optional[Path]:
    """保存結果"""
    if df is None or df.empty:
        logger.warning("⚠️ 沒有數據可保存")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    try:
        # 今日總滙
        today_file = OUTPUT_DIR / f'爬蟲潛客總滙_{timestamp}.xlsx'
        df.to_excel(today_file, index=False, engine='openpyxl')
        logger.info(f"\n💾 已保存: {today_file}")
        
        # 最新總滙（覆蓋）
        latest_file = OUTPUT_DIR / '爬蟲潛客總滙_最新.xlsx'
        df.to_excel(latest_file, index=False, engine='openpyxl')
        logger.info(f"💾 已更新: {latest_file}")
        
        # 統計
        logger.info(f"\n📈 統計:")
        if '平台' in df.columns:
            logger.info(df['平台'].value_counts().to_string())
        logger.info(f"總計: {len(df)} 筆")
        
        return today_file
    except Exception as e:
        logger.error(f"保存結果失敗: {e}")
        return None


def backup_existing():
    """備份現有總滙檔案"""
    latest = OUTPUT_DIR / '爬蟲潛客總滙_最新.xlsx'
    if latest.exists():
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            backup_name = f'爬蟲潛客總滙_備份_{timestamp}.xlsx'
            shutil.copy(latest, BACKUP_DIR / backup_name)
            logger.info(f"💾 已備份舊檔案: {backup_name}")
        except Exception as e:
            logger.warning(f"備份失敗: {e}")


def main():
    """主程序"""
    start_time = time.time()
    
    print("="*60)
    print("🦞 爬蟲潛客整合系統 (優化版)")
    print(f"⏰ 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        ensure_dirs()
        backup_existing()
        
        # 導出數據
        print("\n📥 導出數據...")
        df28 = export_28car_to_excel()
        df_fb = export_fb_to_excel()
        
        # 合併去重
        print("\n🔄 合併去重...")
        combined = merge_and_deduplicate(df28, df_fb)
        
        # 保存結果
        if combined is not None:
            save_results(combined)
            print("\n✅ 完成！")
        else:
            print("\n❌ 沒有生成檔案")
        
    except Exception as e:
        logger.error(f"程序執行出錯: {e}", exc_info=True)
        print(f"\n❌ 錯誤: {e}")
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️  執行耗時: {elapsed_time:.2f} 秒")
    print("="*60)


if __name__ == "__main__":
    main()
