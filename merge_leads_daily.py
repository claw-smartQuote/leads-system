#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
潛客系統總滙腳本
每天整合所有潛客資料，去重並排序
"""

import pandas as pd
import os
import glob
from datetime import datetime
import shutil

# 設置
DATA_DIR = "/Users/claw/Desktop/潛客系統"
OUTPUT_FILE = os.path.join(DATA_DIR, "潛客系統總滙.xlsx")
BACKUP_DIR = os.path.join(DATA_DIR, "備份")

def merge_leads():
    """整合所有潛客資料檔"""
    
    # 確保目錄存在
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # 查找所有潛客資料檔案（排除總滙檔案本身）
    pattern = os.path.join(DATA_DIR, "潛客資料_*.xlsx")
    files = glob.glob(pattern)
    
    if not files:
        print(f"{datetime.now()} - 沒有找到潛客資料檔案")
        return
    
    print(f"{datetime.now()} - 找到 {len(files)} 個資料檔案")
    
    # 讀取所有檔案
    all_data = []
    for file_path in sorted(files):
        try:
            df = pd.read_excel(file_path)
            if not df.empty:
                all_data.append(df)
                print(f"  ✓ {os.path.basename(file_path)}: {len(df)} 筆")
        except Exception as e:
            print(f"  ✗ {os.path.basename(file_path)}: {e}")
    
    if not all_data:
        print(f"{datetime.now()} - 沒有可整合的數據")
        return
    
    # 合併所有數據
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"{datetime.now()} - 合併完成，共 {len(combined_df)} 筆資料")
    
    # 去重：根據「車牌」和「電話」兩個欄位都相同才去重，保留最新的（提交時間最晚的）
    if '車牌' in combined_df.columns and '電話' in combined_df.columns:
        # 先按提交時間排序（最新的在後面）
        if '提交時間' in combined_df.columns:
            combined_df['提交時間'] = pd.to_datetime(combined_df['提交時間'], errors='coerce')
            combined_df = combined_df.sort_values('提交時間')
        
        # 根據車牌+電話去重，保留最後一條（最新的）
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['車牌', '電話'], keep='last')
        after_count = len(combined_df)
        removed_count = before_count - after_count
        print(f"{datetime.now()} - 去重完成（車牌+電話），刪除 {removed_count} 筆重複資料，剩餘 {after_count} 筆")
    elif '電話' in combined_df.columns:
        # 如果沒有車牌欄位，則只根據電話去重
        if '提交時間' in combined_df.columns:
            combined_df['提交時間'] = pd.to_datetime(combined_df['提交時間'], errors='coerce')
            combined_df = combined_df.sort_values('提交時間')
        
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['電話'], keep='last')
        after_count = len(combined_df)
        removed_count = before_count - after_count
        print(f"{datetime.now()} - 去重完成（僅電話），刪除 {removed_count} 筆重複資料，剩餘 {after_count} 筆")
    
    # 按編號排序
    if '編號' in combined_df.columns:
        combined_df = combined_df.sort_values('編號')
    
    # 重新編號（可選：如果需要連續編號）
    # combined_df['編號'] = range(1, len(combined_df) + 1)
    
    # 保存總滙檔案
    combined_df.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')
    print(f"{datetime.now()} - 總滙檔案已保存: {OUTPUT_FILE}")
    print(f"  📊 總計: {len(combined_df)} 筆潛客資料")
    
    # 備份已處理的檔案（移動到備份文件夾）
    for file_path in files:
        try:
            filename = os.path.basename(file_path)
            backup_path = os.path.join(BACKUP_DIR, filename)
            shutil.move(file_path, backup_path)
        except Exception as e:
            print(f"  ✗ 備份失敗 {filename}: {e}")
    
    print(f"{datetime.now()} - 整合完成！")

if __name__ == "__main__":
    merge_leads()