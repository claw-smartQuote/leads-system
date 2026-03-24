#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
個人秘書 - 刪除提醒
"""

import json
import os
import argparse
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.openclaw/workspace/memory/personal_reminders.json")

def load_reminders():
    """讀取提醒數據"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_reminders(data):
    """保存提醒數據"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def delete_reminder(reminder_type, name_keyword):
    """刪除提醒"""
    data = load_reminders()
    
    # 類型對應
    type_mapping = {
        "task": "tasks",
        "tasks": "tasks",
        "bill": "bills",
        "bills": "bills",
        "account": "accounts",
        "accounts": "accounts",
        "event": "events",
        "events": "events",
        "anniversary": "anniversaries",
        "anniversaries": "anniversaries"
    }
    
    type_key = type_mapping.get(reminder_type, reminder_type)
    
    if type_key not in data:
        print(f"❌ 類型 '{reminder_type}' 不存在")
        return False
    
    items = data[type_key]
    original_count = len(items)
    
    # 查找並刪除匹配項目
    deleted = []
    remaining = []
    
    for item in items:
        if name_keyword.lower() in item.get("name", "").lower():
            deleted.append(item)
        else:
            remaining.append(item)
    
    if not deleted:
        print(f"❌ 沒有找到包含 '{name_keyword}' 的提醒")
        return False
    
    # 確認刪除
    print(f"找到 {len(deleted)} 項匹配：")
    for item in deleted:
        print(f"  • {item.get('name')} ({item.get('due_date')})")
    
    # 執行刪除
    data[type_key] = remaining
    save_reminders(data)
    
    print(f"✅ 已刪除 {len(deleted)} 項提醒")
    return True

def main():
    parser = argparse.ArgumentParser(description='刪除個人提醒')
    parser.add_argument('--type', required=True,
                       choices=['task', 'tasks', 'bill', 'bills', 'account', 'accounts', 
                               'event', 'events', 'anniversary', 'anniversaries'],
                       help='提醒類型')
    parser.add_argument('--name', required=True, help='名稱關鍵字')
    
    args = parser.parse_args()
    
    delete_reminder(args.type, args.name)

if __name__ == "__main__":
    main()