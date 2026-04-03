#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全數據庫潛客整合腳本 (終極優化版)
整合所有 11+ 個數據庫，去重並生成總滙

修復內容:
1. 添加所有 11 個數據庫的讀取支持
2. 添加 SQLite 超時設置和重試機制
3. 使用 WAL 模式避免鎖表
4. 批量處理和事務優化
5. 添加詳細日誌記錄和性能監控
"""

import pandas as pd
import sqlite3
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import shutil
import functools

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'/Users/claw/.openclaw/workspace/logs/merge_leads_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)

# 設定
WORKSPACE = Path('/Users/claw/.openclaw/workspace')
OUTPUT_DIR = WORKSPACE / '爬蟲潛客總滙'
BACKUP_DIR = OUTPUT_DIR / '備份'
LOG_DIR = WORKSPACE / 'logs'

# 所有數據庫配置 (11個)
DATABASES = {
    # 28car 數據庫 (4個)
    'car28_main': WORKSPACE / 'car28_scraper.db',
    'car28_loose': WORKSPACE / 'car28_scraper_loose.db',
    'car28_v3': WORKSPACE / 'car28_scraper_v3.db',
    'car28_v4': WORKSPACE / 'car28_scraper_v4.db',
    
    # Facebook 數據庫 (7個)
    'fb_final': WORKSPACE / 'fb_leads_final.db',
    'fb_group': WORKSPACE / 'fb_group_leads.db',
    'fb_page': WORKSPACE / 'fb_page_leads.db',
    'fb_search': WORKSPACE / 'fb_leads_search.db',
    'fb_quick': WORKSPACE / 'fb_quick.db',
    'fb_single': WORKSPACE / 'fb_single_post.db',
    'fb_stable': WORKSPACE / 'fb_stable.db',
}

# SQLite 連接配置
SQLITE_TIMEOUT = 60  # 增加到 60 秒
MAX_RETRIES = 5      # 增加到 5 次重試
RETRY_DELAY = 3      # 增加到 3 秒
BATCH_SIZE = 500     # 批量處理大小


def timer_decorator(func):
    """性能計時裝飾器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        logger.info(f"開始執行: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"完成: {func.__name__} (耗時: {elapsed:.2f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"失敗: {func.__name__} (耗時: {elapsed:.2f}s) - {e}")
            raise
    return wrapper


def ensure_dirs():
    """確保目錄存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"目錄檢查完成")


def connect_with_retry(db_path: Path, max_retries: int = MAX_RETRIES) -> Optional[sqlite3.Connection]:
    """
    帶重試機制的 SQLite 連接
    
    Args:
        db_path: 數據庫文件路徑
        max_retries: 最大重試次數
        
    Returns:
        sqlite3.Connection 或 None
    """
    if not db_path.exists():
        logger.warning(f"數據庫不存在: {db_path}")
        return None
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(
                str(db_path),
                timeout=SQLITE_TIMEOUT,
                isolation_level=None  # 自動提交模式
            )
            # 設置 WAL 模式以提高並發性能
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")  # 60秒超時
            conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全性
            logger.debug(f"成功連接數據庫: {db_path.name}")
            return conn
        except sqlite3.Error as e:
            logger.warning(f"數據庫連接失敗 (嘗試 {attempt + 1}/{max_retries}): {db_path.name} - {e}")
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # 指數退避
                logger.info(f"等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
            else:
                logger.error(f"數據庫連接最終失敗: {db_path.name}")
                return None
    return None


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> List[Tuple]:
    """獲取表結構"""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logger.warning(f"獲取表結構失敗: {table_name} - {e}")
        return []


def export_db_to_dataframe(db_path: Path, db_name: str) -> Optional[pd.DataFrame]:
    """
    從數據庫導出到 DataFrame (批量處理)
    
    Args:
        db_path: 數據庫路徑
        db_name: 數據庫名稱
        
    Returns:
        pd.DataFrame 或 None
    """
    conn = connect_with_retry(db_path)
    if not conn:
        return None
    
    try:
        # 獲取所有表名
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
        
        if not tables:
            logger.warning(f"{db_name}: 沒有找到數據表")
            return None
        
        all_data = []
        
        for table in tables:
            try:
                # 檢查表是否有數據
                count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = count_cursor.fetchone()[0]
                
                if count == 0:
                    continue
                
                logger.info(f"{db_name}.{table}: {count} 筆數據")
                
                # 分批讀取數據
                offset = 0
                while offset < count:
                    query = f"SELECT * FROM {table} LIMIT {BATCH_SIZE} OFFSET {offset}"
                    batch_df = pd.read_sql_query(query, conn)
                    
                    if not batch_df.empty:
                        # 添加元數據
                        batch_df['_source_db'] = db_name
                        batch_df['_source_table'] = table
                        batch_df['_exported_at'] = datetime.now().isoformat()
                        all_data.append(batch_df)
                    
                    offset += BATCH_SIZE
                    
            except Exception as e:
                logger.warning(f"讀取表失敗: {db_name}.{table} - {e}")
                continue
        
        if not all_data:
            return None
        
        # 合併所有數據
        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"✅ {db_name}: 成功導出 {len(combined)} 筆")
        return combined
        
    except Exception as e:
        logger.error(f"導出數據庫失敗: {db_name} - {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass


@timer_decorator
def export_all_databases() -> Dict[str, pd.DataFrame]:
    """
    導出所有數據庫
    
    Returns:
        Dict[str, pd.DataFrame]: 數據庫名稱到 DataFrame 的映射
    """
    results = {}
    total_records = 0
    
    logger.info("="*60)
    logger.info("開始導出所有數據庫...")
    logger.info("="*60)
    
    for db_name, db_path in DATABASES.items():
        df = export_db_to_dataframe(db_path, db_name)
        if df is not None and not df.empty:
            results[db_name] = df
            total_records += len(df)
    
    logger.info("="*60)
    logger.info(f"導出完成: {len(results)}/{len(DATABASES)} 個數據庫, 共 {total_records} 筆")
    logger.info("="*60)
    
    return results


@timer_decorator
def merge_and_deduplicate(dataframes: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    合併所有數據並去重
    
    Args:
        dataframes: 數據庫名稱到 DataFrame 的映射
        
    Returns:
        pd.DataFrame 或 None
    """
    if not dataframes:
        logger.warning("⚠️ 沒有可合併的數據")
        return None
    
    logger.info("開始合併和去重...")
    
    # 合併所有數據
    all_data = list(dataframes.values())
    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"合併完成: {len(combined)} 筆原始數據")
    
    # 智能去重策略
    before_count = len(combined)
    
    # 1. 嘗試根據電話號碼去重
    phone_columns = [col for col in combined.columns if 'phone' in col.lower() or '電話' in col]
    if phone_columns:
        phone_col = phone_columns[0]
        logger.info(f"使用 '{phone_col}' 欄位進行去重")
        
        # 清理電話號碼格式
        combined[phone_col] = combined[phone_col].astype(str).str.replace(r'\D', '', regex=True)
        
        # 按導出時間排序（保留最新的）
        if '_exported_at' in combined.columns:
            combined = combined.sort_values('_exported_at')
        
        # 去重
        combined = combined.drop_duplicates(subset=[phone_col], keep='last')
    else:
        # 2. 如果沒有電話欄位，嘗試根據所有欄位去重
        logger.info("沒有找到電話欄位，使用所有欄位去重")
        combined = combined.drop_duplicates(keep='last')
    
    after_count = len(combined)
    removed_count = before_count - after_count
    
    logger.info(f"🔍 去重完成: 刪除 {removed_count} 筆重複，剩餘 {after_count} 筆")
    
    return combined


@timer_decorator
def save_results(df: pd.DataFrame) -> Optional[Path]:
    """
    保存結果到 Excel
    
    Args:
        df: 要保存的 DataFrame
        
    Returns:
        Path 或 None
    """
    if df is None or df.empty:
        logger.warning("⚠️ 沒有數據可保存")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    try:
        # 分批寫入 Excel (避免內存問題)
        logger.info("開始保存 Excel 文件...")
        
        # 今日總滙
        today_file = OUTPUT_DIR / f'全潛客總滙_{timestamp}.xlsx'
        
        # 使用 ExcelWriter
        with pd.ExcelWriter(today_file, engine='openpyxl') as writer:
            # 主數據表
            df.to_excel(writer, sheet_name='全部潛客', index=False)
            
            # 按數據庫來源統計
            if '_source_db' in df.columns:
                source_stats = df['_source_db'].value_counts().reset_index()
                source_stats.columns = ['數據庫來源', '數量']
                source_stats.to_excel(writer, sheet_name='來源統計', index=False)
            
            # 數據質量報告
            quality_data = []
            for col in df.columns:
                if not col.startswith('_'):
                    non_null = df[col].notna().sum()
                    quality_data.append({
                        '欄位名稱': col,
                        '非空數量': non_null,
                        '非空比例': f"{non_null/len(df)*100:.1f}%"
                    })
            
            if quality_data:
                pd.DataFrame(quality_data).to_excel(writer, sheet_name='數據質量', index=False)
        
        logger.info(f"💾 已保存: {today_file}")
        
        # 最新總滙（覆蓋）
        latest_file = OUTPUT_DIR / '全潛客總滙_最新.xlsx'
        shutil.copy(today_file, latest_file)
        logger.info(f"💾 已更新: {latest_file}")
        
        # 輸出統計
        logger.info(f"\n📈 統計摘要:")
        logger.info(f"  總記錄數: {len(df)}")
        logger.info(f"  欄位數: {len(df.columns)}")
        if '_source_db' in df.columns:
            logger.info(f"  來源分布:")
            for source, count in df['_source_db'].value_counts().items():
                logger.info(f"    - {source}: {count} 筆")
        
        return today_file
        
    except Exception as e:
        logger.error(f"保存結果失敗: {e}", exc_info=True)
        return None


def backup_existing():
    """備份現有總滙檔案"""
    latest = OUTPUT_DIR / '全潛客總滙_最新.xlsx'
    if latest.exists():
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            backup_name = f'全潛客總滙_備份_{timestamp}.xlsx'
            shutil.copy(latest, BACKUP_DIR / backup_name)
            logger.info(f"💾 已備份舊檔案: {backup_name}")
        except Exception as e:
            logger.warning(f"備份失敗: {e}")


@timer_decorator
def main():
    """主程序"""
    start_time = time.time()
    
    print("="*70)
    print("🦞 全數據庫潛客整合系統 (終極優化版)")
    print(f"⏰ 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 目標數據庫: {len(DATABASES)} 個")
    print("="*70)
    
    try:
        # 初始化
        ensure_dirs()
        backup_existing()
        
        # 導出所有數據庫
        logger.info("\n📥 步驟 1/3: 導出所有數據庫...")
        dataframes = export_all_databases()
        
        if not dataframes:
            logger.error("❌ 沒有成功導出任何數據庫")
            return
        
        # 合併去重
        logger.info("\n🔄 步驟 2/3: 合併去重...")
        combined = merge_and_deduplicate(dataframes)
        
        if combined is None:
            logger.error("❌ 合併失敗")
            return
        
        # 保存結果
        logger.info("\n💾 步驟 3/3: 保存結果...")
        result_file = save_results(combined)
        
        if result_file:
            print("\n" + "="*70)
            print("✅ 整合完成！")
            print(f"📁 輸出文件: {result_file}")
            print(f"📊 總記錄數: {len(combined)} 筆")
            print("="*70)
        else:
            print("\n❌ 保存結果失敗")
        
    except Exception as e:
        logger.error(f"程序執行出錯: {e}", exc_info=True)
        print(f"\n❌ 錯誤: {e}")
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️  總執行耗時: {elapsed_time:.2f} 秒")
    print("="*70)


if __name__ == "__main__":
    main()
