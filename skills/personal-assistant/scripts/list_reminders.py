#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
個人秘書 - 列出所有提醒
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

def list_reminders(reminder_type="all", status=None):
    """列出提醒"""
    data = load_reminders()
    
    type_names = {
        "tasks": "📋 待辦事項",
        "bills": "💰 帳單",
        "accounts": "🔐 賬號",
        "events": "⭐ 重要事項",
        "anniversaries": "🎉 紀念日"
    }
    
    types_to_show = [reminder_type] if reminder_type != "all" else data.keys()
    
    for rt in types_to_show:
        if rt not in data:
            continue
            
        type_name = type_names.get(rt, rt)
        items = data[rt]
        
        if status:
            items = [i for i in items if i.get("status") == status]
        
        # 按到期日排序
        items.sort(key=lambda x: x.get("due_date", ""))
        
        print(f"\n{type_name} ({len(items)}項):")
        print("-" * 50)
        
        if not items:
            print("  (無)")
            continue
        
        for item in items:
            status_icon = "✅" if item.get("status") == "completed" else "⏳"
            name = item.get("name", "")
            due = item.get("due_date", "")
            priority = item.get("priority", "medium")
            
            # 計算剩餘天數
            try:
                due_date = datetime.strptime(due, "%Y-%m-%d")
                days_left = (due_date - datetime.now()).days
                if days_left < 0:
                    days_text = f"⚠️ 逾期{abs(days_left)}天"
                elif days_left == 0:
                    days_text = "🔴 今天"
                elif days_left == 1:
                    days_text = "📅 明天"
                else:
                    days_text = f"還有{days_left}天"
            except:
                days_text = ""
            
            print(f"  {status_icon} {name}")
            print(f"     到期: {due} ({days_text})", end="")
            
            if item.get("amount"):
                print(f" | 金額: ${item['amount']}", end="")
            
            priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(f" | {priority_icons.get(priority, '⚪')} {priority}")
            
            if item.get("notes"):
                print(f"     備註: {item['notes']}")

def main():
    parser = argparse.ArgumentParser(description='列出個人提醒')
    parser.add_argument('--type', default='all',
                       choices=['all', 'tasks', 'bills', 'accounts', 'events', 'anniversaries'],
                       help='提醒類型')
    parser.add_argument('--status', choices=['pending', 'completed'],
                       help='狀態過濾')
    
    args = parser.parse_args()
    
    print(f"📋 個人提醒清單 ({datetime.now().strftime('%Y-%m-%d')})")
    list_reminders(args.type, args.status)

if __name__ == "__main__":
    main()