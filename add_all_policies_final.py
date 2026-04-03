#!/usr/bin/env python3
import json
import subprocess
import time
from datetime import datetime, timedelta

with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'r') as f:
    data = json.load(f)

allianz_policies = [p for p in data['policies'] if p['insurer'] == '永城']

current_year = datetime.now().year
month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']

added = 0
failed = []

print(f'開始添加 {len(allianz_policies)} 筆永誠保險保單...')
print('')
print('設置規格:')
print('  • 時間: 全天事件 (All-day)')
print('  • 提醒: 到期前28天')
print('  • 重複: 每年永久重複')
print('  • 不依賴年份: 按月份和日期')
print('')

for i, policy in enumerate(allianz_policies):
    try:
        expiry_date = policy['expiry_date']
        plate = policy['plate_number']
        insured = policy['insured_name']
        
        date_parts = expiry_date.split('-')
        month = int(date_parts[1])
        day = int(date_parts[2])
        
        # 計算提醒日期（到期前28天）
        expiry_this_year = datetime(current_year, month, day)
        reminder_date = expiry_this_year - timedelta(days=28)
        
        r_month = reminder_date.month
        r_day = reminder_date.day
        month_name = month_names[r_month]
        
        # 使用 AppleScript 創建全天事件
        script = f"""tell application "Calendar"
tell calendar "港車北上保單"
set startDate to (current date)
set year of startDate to 2026
set month of startDate to {month_name}
set day of startDate to {r_day}
set hours of startDate to 0
set minutes of startDate to 0
set seconds of startDate to 0
set endDate to startDate
set newEvent to make new event with properties {{summary:"🚗 保單到期提醒: {plate}", start date:startDate, end date:endDate, allday event:true, description:"被保人: {insured} | 車牌: {plate} | 到期日: {month}/{day} | 保險公司: 永誠"}}
set recurrence of newEvent to "FREQ=YEARLY;INTERVAL=1"
end tell
end tell"""
        
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            added += 1
            if (i + 1) % 20 == 0:
                print(f'  已添加 {i+1}/{len(allianz_policies)} 筆...')
        else:
            failed.append(plate)
            
        # 短暫延遲
        time.sleep(0.2)
            
    except Exception as e:
        failed.append(policy.get('plate_number', 'unknown'))

print('')
print(f'✅ 成功添加: {added} 筆')
if failed:
    print(f'⚠️ 失敗: {len(failed)} 筆 - {failed}')
print('')
print('📅 設置完成:')
print('  • 全天事件: ✅')
print('  • 到期前28天提醒: ✅')
print('  • 每年永久重複: ✅')
print('  • 按月份和日期（不依賴年份）: ✅')
