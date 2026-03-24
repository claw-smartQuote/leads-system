#!/usr/bin/env python3
"""
保單到期提醒管理系統
Insurance Policy Renewal Reminder System
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# 數據文件路徑
DATA_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
POLICY_FILE = DATA_DIR / "policies.json"


def ensure_data_dir():
    """確保數據目錄存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_policies():
    """加載保單數據"""
    if POLICY_FILE.exists():
        with open(POLICY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"policies": [], "last_check": None}


def save_policies(data):
    """保存保單數據"""
    ensure_data_dir()
    with open(POLICY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_date(date_str, year=2024):
    """解析日期字符串"""
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # 嘗試多種格式
    formats = [
        f"{year}.%m.%d",
        f"{year}-%m-%d",
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%m.%d",
        "%m-%d",
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # 如果沒有年份，使用默認年份
            if parsed.year == 1900:
                parsed = parsed.replace(year=year)
            return parsed
        except ValueError:
            continue
    
    # 嘗試處理單個數字（如 "6.2" 表示 6月2日）
    try:
        if '.' in date_str:
            parts = date_str.split('.')
            month = int(parts[0])
            day = int(parts[1])
            return datetime(year, month, day)
    except (ValueError, IndexError):
        pass
    
    return None


def import_from_excel(excel_path, owner=None):
    """從 Excel 導入保單數據"""
    try:
        import openpyxl
    except ImportError:
        print("❌ 需要安裝 openpyxl: pip3 install openpyxl")
        return False
    
    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在: {excel_path}")
        return False
    
    print(f"📖 正在讀取: {excel_path}")
    
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active
        
        policies_data = load_policies()
        existing_plates = {p['plate_number'] for p in policies_data['policies']}
        
        imported_count = 0
        
        # 遍歷數據行（假設第一行是標題）
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:  # 跳過空行
                continue
            
            # 解析數據 (出单日期, 到期日, 出单人, 保险公司, 车牌号, 被保人)
            issue_date = parse_date(row[0])
            expiry_date = parse_date(row[1])
            
            if not expiry_date:
                continue
            
            agent = row[2] or owner or "未知"
            insurer = row[3] or "永城"
            plate_number = row[4]
            insured_name = row[5]
            
            if not plate_number:
                continue
            
            # 檢查是否已存在
            if plate_number in existing_plates:
                continue
            
            policy = {
                "id": str(uuid.uuid4()),
                "issue_date": issue_date.strftime("%Y-%m-%d") if issue_date else None,
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "agent": agent,
                "insurer": insurer,
                "plate_number": plate_number,
                "insured_name": insured_name,
                "reminder_sent": False,
                "calendar_added": False,
                "imported_at": datetime.now().isoformat()
            }
            
            policies_data['policies'].append(policy)
            imported_count += 1
            print(f"  ✅ 導入: {plate_number} - {insured_name} (到期: {expiry_date.strftime('%Y-%m-%d')})")
        
        save_policies(policies_data)
        print(f"\n📊 成功導入 {imported_count} 筆保單")
        return True
        
    except Exception as e:
        print(f"❌ 讀取失敗: {e}")
        return False


def add_to_calendar(days_before=7):
    """將到期日添加到 Apple 日曆"""
    policies_data = load_policies()
    
    added_count = 0
    
    for policy in policies_data['policies']:
        if policy.get('calendar_added'):
            continue
        
        try:
            expiry = datetime.strptime(policy['expiry_date'], "%Y-%m-%d")
            reminder_date = expiry - timedelta(days=days_before)
            
            # 使用 AppleScript 添加提醒
            title = f"🚗 保單到期提醒: {policy['plate_number']}"
            notes = f"""
被保人: {policy['insured_name']}
車牌號: {policy['plate_number']}
保險公司: {policy['insurer']}
到期日: {policy['expiry_date']}
出單人: {policy['agent']}
"""
            
            # 使用 osascript 添加到提醒事項 (Reminders)
            script = f'''
tell application "Reminders"
    tell list "提醒事項" of default account
        make new reminder with properties {{name:"{title}", body:"{notes}", due date:date "{reminder_date.strftime('%Y-%m-%d')}"}}
    end tell
end tell
'''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                policy['calendar_added'] = True
                added_count += 1
                print(f"✅ 已添加提醒: {policy['plate_number']} - {reminder_date.strftime('%Y-%m-%d')}")
            else:
                # 如果 Reminders 失敗，嘗試 Calendar
                cal_script = f'''
tell application "Calendar"
    tell calendar "Home"
        make new event with properties {{summary:"{title}", start date:date "{reminder_date.strftime('%Y-%m-%d')} 09:00:00", end date:date "{reminder_date.strftime('%Y-%m-%d')} 09:30:00", description:"{notes}"}}
    end tell
end tell
'''
                result = subprocess.run(
                    ['osascript', '-e', cal_script],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    policy['calendar_added'] = True
                    added_count += 1
                    print(f"✅ 已添加日曆事件: {policy['plate_number']}")
                
        except Exception as e:
            print(f"❌ 添加失敗 {policy['plate_number']}: {e}")
    
    save_policies(policies_data)
    print(f"\n📅 共添加 {added_count} 個提醒")
    return True


def check_expiring(days=30):
    """檢查即將到期的保單"""
    policies_data = load_policies()
    
    today = datetime.now()
    cutoff_date = today + timedelta(days=days)
    
    expiring = []
    
    for policy in policies_data['policies']:
        try:
            expiry = datetime.strptime(policy['expiry_date'], "%Y-%m-%d")
            
            # 檢查是否在即將到期的範圍內，且尚未發送提醒
            if today <= expiry <= cutoff_date and not policy.get('reminder_sent'):
                days_left = (expiry - today).days
                policy['days_left'] = days_left
                expiring.append(policy)
                
        except Exception as e:
            continue
    
    # 按剩餘天數排序
    expiring.sort(key=lambda x: x['days_left'])
    
    return expiring


def format_reminder_message(policies):
    """格式化提醒消息"""
    if not policies:
        return None
    
    message = "📋 *保單到期提醒*\n\n"
    
    for p in policies:
        message += f"🚗 *{p['plate_number']}*\n"
        message += f"   被保人: {p['insured_name']}\n"
        message += f"   到期日: {p['expiry_date']}\n"
        message += f"   還有 *{p['days_left']}* 天\n\n"
    
    message += "請聯繫客戶辦理續保事宜。"
    
    return message


def send_whatsapp_reminder(phone_number, policies):
    """通過 WhatsApp 發送提醒"""
    if not policies:
        print("✅ 沒有需要提醒的保單")
        return True
    
    message = format_reminder_message(policies)
    
    if not message:
        return False
    
    print(f"📱 正在發送提醒到 {phone_number}...")
    print(f"📨 消息內容:\n{message}\n")
    
    # 使用 wacli 發送
    try:
        # 先創建臨時文件存儲消息
        temp_file = DATA_DIR / "temp_reminder.txt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(message)
        
        # 使用 wacli 發送
        cmd = ['wacli', 'send', 'text', '--to', phone_number, '--message', message]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 or "sent" in result.stdout.lower():
            print(f"✅ WhatsApp 提醒已發送")
            return True
        else:
            print(f"⚠️ 發送可能成功，請檢查 WhatsApp")
            return True
            
    except Exception as e:
        print(f"❌ 發送失敗: {e}")
        # 打印消息，讓用戶可以手動發送
        print(f"\n請手動發送以下消息到 {phone_number}:")
        print("=" * 50)
        print(message)
        print("=" * 50)
        return False


def mark_reminders_sent(policies):
    """標記提醒已發送"""
    policies_data = load_policies()
    
    sent_ids = {p['id'] for p in policies}
    
    for policy in policies_data['policies']:
        if policy['id'] in sent_ids:
            policy['reminder_sent'] = True
            policy['reminder_sent_at'] = datetime.now().isoformat()
    
    policies_data['last_check'] = datetime.now().isoformat()
    save_policies(policies_data)


def auto_check_and_remind(phone_number, days=30):
    """自動檢查並發送提醒"""
    print(f"🔍 檢查未來 {days} 天內到期的保單...\n")
    
    expiring = check_expiring(days)
    
    if not expiring:
        print("✅ 沒有即將到期的保單")
        return True
    
    print(f"📊 發現 {len(expiring)} 筆即將到期的保單:\n")
    for p in expiring:
        print(f"  🚗 {p['plate_number']} - {p['insured_name']} ({p['days_left']} 天)")
    
    print(f"\n📱 正在發送 WhatsApp 提醒...")
    
    if send_whatsapp_reminder(phone_number, expiring):
        mark_reminders_sent(expiring)
        print(f"\n✅ 已完成 {len(expiring)} 筆保單的到期提醒")
        return True
    
    return False


def list_all_policies():
    """列出所有保單"""
    policies_data = load_policies()
    
    if not policies_data['policies']:
        print("📭 沒有保單記錄")
        return
    
    print(f"\n📋 共有 {len(policies_data['policies'])} 筆保單:\n")
    print(f"{'車牌號':<15} {'被保人':<12} {'到期日':<12} {'提醒':<8} {'日曆':<8}")
    print("-" * 65)
    
    for p in sorted(policies_data['policies'], key=lambda x: x['expiry_date']):
        reminder_status = "✅" if p.get('reminder_sent') else "⏳"
        calendar_status = "✅" if p.get('calendar_added') else "⏳"
        print(f"{p['plate_number']:<15} {p['insured_name']:<12} {p['expiry_date']:<12} {reminder_status:<8} {calendar_status:<8}")


def reset_reminders():
    """重置提醒狀態（用於測試）"""
    policies_data = load_policies()
    
    for policy in policies_data['policies']:
        policy['reminder_sent'] = False
        policy['calendar_added'] = False
    
    save_policies(policies_data)
    print("🔄 提醒狀態已重置")


def main():
    parser = argparse.ArgumentParser(description='保單到期提醒管理系統')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # import 命令
    import_parser = subparsers.add_parser('import', help='從 Excel 導入保單')
    import_parser.add_argument('excel_path', help='Excel 文件路徑')
    import_parser.add_argument('--owner', help='出單人名稱')
    
    # add-to-calendar 命令
    calendar_parser = subparsers.add_parser('add-to-calendar', help='添加到日曆')
    calendar_parser.add_argument('--days-before', type=int, default=7, help='提前幾天提醒')
    
    # check 命令
    check_parser = subparsers.add_parser('check', help='檢查即將到期的保單')
    check_parser.add_argument('--days', type=int, default=30, help='檢查未來幾天')
    
    # send-reminders 命令
    send_parser = subparsers.add_parser('send-reminders', help='發送 WhatsApp 提醒')
    send_parser.add_argument('--days', type=int, default=30, help='提前幾天提醒')
    send_parser.add_argument('--to', required=True, help='接收提醒的 WhatsApp 號碼')
    
    # auto 命令
    auto_parser = subparsers.add_parser('auto', help='自動檢查並發送提醒')
    auto_parser.add_argument('--days', type=int, default=30, help='提前幾天提醒')
    auto_parser.add_argument('--to', required=True, help='接收提醒的 WhatsApp 號碼')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有保單')
    
    # reset 命令
    subparsers.add_parser('reset', help='重置提醒狀態')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 執行命令
    if args.command == 'import':
        import_from_excel(args.excel_path, args.owner)
    elif args.command == 'add-to-calendar':
        add_to_calendar(args.days_before)
    elif args.command == 'check':
        expiring = check_expiring(args.days)
        if expiring:
            print(f"\n📊 未來 {args.days} 天內有 {len(expiring)} 筆保單到期:\n")
            for p in expiring:
                print(f"  🚗 {p['plate_number']} - {p['insured_name']} ({p['days_left']} 天)")
        else:
            print(f"\n✅ 未來 {args.days} 天內沒有保單到期")
    elif args.command == 'send-reminders':
        expiring = check_expiring(args.days)
        if send_whatsapp_reminder(args.to, expiring):
            mark_reminders_sent(expiring)
    elif args.command == 'auto':
        auto_check_and_remind(args.to, args.days)
    elif args.command == 'list':
        list_all_policies()
    elif args.command == 'reset':
        reset_reminders()


if __name__ == '__main__':
    main()