#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
個人秘書 - 每日檢查提醒
"""

import json
import os
from datetime import datetime, timedelta

DATA_FILE = os.path.expanduser("~/.openclaw/workspace/memory/personal_reminders.json")

def load_reminders():
    """讀取提醒數據"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def check_reminders():
    """檢查即將到期的提醒"""
    data = load_reminders()
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    week_later = today + timedelta(days=7)
    
    alerts = {
        "today": [],
        "tomorrow": [],
        "this_week": []
    }
    
    type_names = {
        "tasks": "📋 待辦事項",
        "bills": "💰 帳單",
        "accounts": "🔐 賬號",
        "events": "⭐ 重要事項",
        "anniversaries": "🎉 紀念日"
    }
    
    for reminder_type, items in data.items():
        type_name = type_names.get(reminder_type, reminder_type)
        
        for item in items:
            if item.get("status") == "completed":
                continue
                
            due_str = item.get("due_date", "")
            try:
                due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
            except:
                continue
            
            # 計算天數差
            days_diff = (due_date - today).days
            
            alert_item = {
                "type": type_name,
                "name": item.get("name", ""),
                "due_date": due_str,
                "days_left": days_diff,
                "details": item
            }
            
            if days_diff == 0:
                alerts["today"].append(alert_item)
            elif days_diff == 1:
                alerts["tomorrow"].append(alert_item)
            elif 2 <= days_diff <= 7:
                alerts["this_week"].append(alert_item)
    
    return alerts

def format_alert_message(alerts):
    """格式化提醒消息"""
    messages = []
    
    if alerts["today"]:
        messages.append("⏰ **今天到期**：")
        for item in alerts["today"]:
            msg = f"  • {item['type']}: {item['name']}"
            if item['details'].get('amount'):
                msg += f" (金額: ${item['details']['amount']})"
            messages.append(msg)
        messages.append("")
    
    if alerts["tomorrow"]:
        messages.append("📅 **明天到期**：")
        for item in alerts["tomorrow"]:
            msg = f"  • {item['type']}: {item['name']}"
            if item['details'].get('amount'):
                msg += f" (金額: ${item['details']['amount']})"
            messages.append(msg)
        messages.append("")
    
    if alerts["this_week"]:
        messages.append("📆 **本週到期**：")
        for item in alerts["this_week"]:
            msg = f"  • {item['type']}: {item['name']} ({item['days_left']}天後)"
            if item['details'].get('amount'):
                msg += f" (金額: ${item['details']['amount']})"
            messages.append(msg)
    
    if not any(alerts.values()):
        return "✅ 今天沒有即將到期的事項！"
    
    return "\n".join(messages)

def main():
    """主函數"""
    print(f"🔍 {datetime.now().strftime('%Y-%m-%d %H:%M')} - 檢查提醒事項...")
    
    alerts = check_reminders()
    message = format_alert_message(alerts)
    
    print(message)
    
    # 保存到文件，供其他程序讀取
    alert_file = os.path.expanduser("~/.openclaw/workspace/.daily_reminder_alert")
    with open(alert_file, 'w', encoding='utf-8') as f:
        f.write(message)
    
    return alerts

if __name__ == "__main__":
    main()