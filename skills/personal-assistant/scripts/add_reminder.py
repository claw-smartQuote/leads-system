#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
個人秘書 - 添加提醒事項
"""

import json
import os
import argparse
from datetime import datetime, timedelta

DATA_FILE = os.path.expanduser("~/.openclaw/workspace/memory/personal_reminders.json")

def load_reminders():
    """讀取提醒數據"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "tasks": [],
        "bills": [],
        "accounts": [],
        "events": [],
        "anniversaries": []
    }

def save_reminders(data):
    """保存提醒數據"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_reminder(reminder_type, name, due_date, **kwargs):
    """添加提醒"""
    # 處理特殊的複數形式
    type_mapping = {
        "tasks": "tasks",
        "bills": "bills", 
        "accounts": "accounts",
        "events": "events",
        "anniversarys": "anniversaries"
    }
    reminder_type = type_mapping.get(reminder_type, reminder_type)
    
    data = load_reminders()
    
    reminder = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "name": name,
        "due_date": due_date,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        **kwargs
    }
    
    data[reminder_type].append(reminder)
    save_reminders(data)
    
    print(f"✅ 已添加 {reminder_type}: {name}")
    print(f"   到期日: {due_date}")
    return reminder

def main():
    parser = argparse.ArgumentParser(description='添加個人提醒')
    parser.add_argument('--type', required=True, 
                       choices=['task', 'bill', 'account', 'event', 'anniversary'],
                       help='提醒類型')
    parser.add_argument('--name', required=True, help='名稱')
    parser.add_argument('--due', required=True, help='到期日 (YYYY-MM-DD)')
    parser.add_argument('--amount', help='金額（帳單類）')
    parser.add_argument('--repeat', choices=['none', 'daily', 'weekly', 'monthly', 'yearly'],
                       default='none', help='重複週期')
    parser.add_argument('--notes', help='備註')
    parser.add_argument('--priority', choices=['low', 'medium', 'high'],
                       default='medium', help='優先級')
    
    args = parser.parse_args()
    
    extra = {
        "repeat": args.repeat,
        "priority": args.priority
    }
    
    if args.amount:
        extra["amount"] = args.amount
    if args.notes:
        extra["notes"] = args.notes
    
    add_reminder(args.type + 's', args.name, args.due, **extra)

if __name__ == "__main__":
    main()