#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中國移動電話卡充值提醒更新器
每88天自動更新下一次提醒日期
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

def save_reminders(data):
    """保存提醒數據"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_china_mobile_reminder():
    """更新中國移動充值提醒日期"""
    data = load_reminders()
    
    if "accounts" not in data:
        print("沒有找到賬號提醒")
        return
    
    # 查找中國移動電話卡提醒
    for item in data["accounts"]:
        if "中國移動" in item.get("name", "") and "13537871061" in item.get("name", ""):
            # 計算下一個88天後的日期
            current_due = item.get("due_date", "")
            try:
                due_date = datetime.strptime(current_due, "%Y-%m-%d")
                next_due = due_date + timedelta(days=88)
                next_due_str = next_due.strftime("%Y-%m-%d")
                
                # 更新到期日
                item["due_date"] = next_due_str
                item["status"] = "pending"
                item["updated_at"] = datetime.now().isoformat()
                
                save_reminders(data)
                
                print(f"✅ 已更新中國移動充值提醒")
                print(f"   上一個日期: {current_due}")
                print(f"   下一個日期: {next_due_str} (88天後)")
                print(f"   電話號碼: 13537871061")
                
                # 發送 WhatsApp 通知
                message = f"""⏰ 充值提醒

🇨🇳 中國移動電話卡 (13537871061)
請儘快充值！

下次提醒日期: {next_due_str}
(每88天提醒一次)"""
                
                # 保存通知到文件
                alert_file = os.path.expanduser("~/.openclaw/workspace/.china_mobile_alert")
                with open(alert_file, 'w', encoding='utf-8') as f:
                    f.write(message)
                
                print(f"   📱 提醒通知已準備")
                return
                
            except Exception as e:
                print(f"❌ 更新失敗: {e}")
                return
    
    print("沒有找到中國移動電話卡提醒")

if __name__ == "__main__":
    update_china_mobile_reminder()