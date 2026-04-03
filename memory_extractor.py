#!/usr/bin/env python3
"""
智能記憶提取器
自動分析對話內容並提取重要信息更新到 MEMORY.md
"""

import os
import re
import sys
from datetime import datetime

MEMORY_FILE = os.path.expanduser("~/.openclaw/workspace/MEMORY.md")

def read_memory():
    """讀取現有記憶文件"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return "# MEMORY.md - 長期記憶\n\n"

def extract_key_info(text):
    """從對話中提取關鍵信息"""
    key_info = []
    
    # 提取重要日期
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(下次|到期|提醒).*?(\d{4}-\d{2}-\d{2})',
    ]
    
    # 提取數字信息（保單數量、金額等）
    number_patterns = [
        r'(\d+)\s*份保單',
        r'(\d+)\s*萬',
        r'(\d+)\s*元',
    ]
    
    # 提取關鍵業務信息
    business_patterns = [
        r'(新增|更新|刪除).*?(保單|客戶|報價)',
        r'(續保|到期|提醒)',
    ]
    
    return key_info

def update_memory(new_info):
    """更新記憶文件"""
    memory_content = read_memory()
    
    # 更新最後修改日期
    today = datetime.now().strftime('%Y-%m-%d')
    memory_content = re.sub(
        r'\*最後更新: \d{4}-\d{2}-\d{2}\*',
        f'*最後更新: {today}*',
        memory_content
    )
    
    # 如果有新信息，添加到今日記錄
    if new_info:
        today_section = f"\n### {today}\n"
        if today_section not in memory_content:
            memory_content += f"\n## 📝 每日記錄\n\n### {today}\n"
        
        for info in new_info:
            memory_content += f"- {info}\n"
    
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        f.write(memory_content)
    
    print(f"記憶已更新: {MEMORY_FILE}")

if __name__ == "__main__":
    # 這個腳本可以由 AI 調用來更新記憶
    if len(sys.argv) > 1:
        new_info = sys.argv[1:]
        update_memory(new_info)
    else:
        print("用法: python3 memory_extractor.py '信息1' '信息2' ...")
