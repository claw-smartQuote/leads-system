#!/usr/bin/env python3
import json
import subprocess
import time
from datetime import datetime, timedelta

with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'r') as f:
    data = json.load(f)

allianz_policies = [p for p in data['policies'] if p['insurer'] == '永城']

current_year = datetime.now().year
added = 0
failed = []

print(f'開始添加 {len(allianz_policies)} 筆保單提醒...')
print('')

for i, policy in enumerate(allianz_policies):
    try:
        expiry_date = policy['expiry_date']
        plate = policy['plate_number']
        insured = policy['insured_name']
        
        date_parts = expiry_date.split('-')
        month = int(date_parts[1])
        day = int(date_parts[2])
        
        expiry_this_year = datetime(current_year, month, day)
        reminder_date = expiry_this_year - timedelta(days=28)
        
        r_month = reminder_date.month
        r_day = reminder_date.day
        
        # 使用文件方式執行 AppleScript
        script = f"""tell application "Calendar"
tell calendar "港車北上保單"
set startDate to date "{r_month}/{r_day}/{current_year}"
set endDate to date "{r_month}/{r_day}/{current_year}"
set newEvent to make new event with properties {{summary:"🚗 保單到期提醒: {plate}", start date:startDate, end date:endDate, allday event:true, description:"被保人: {insured} | 車牌: {plate} | 到期日: {month}/{day} | 永誠"}}
set recurrence of newEvent to "FREQ=YEARLY;INTERVAL=1"
end tell
end tell"""
        
        # 寫入臨時文件
        with open(f'/tmp/policy_{i}.scpt', 'w') as f:
            f.write(script)
        
        # 執行腳本
        result = subprocess.run(['osascript', f'/tmp/policy_{i}.scpt'], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            added += 1
        else:
            failed.append(plate)
            
        # 進度報告
        if (i + 1) % 20 == 0:
            print(f'  已處理 {i+1}/{len(allianz_policies)} 筆...')
            
        # 短暫延遲避免過載
        time.sleep(0.1)
            
    except Exception as e:
        failed.append(policy.get('plate_number', 'unknown'))

# 清理臨時文件
import os
for i in range(len(allianz_policies)):
    try:
        os.remove(f'/tmp/policy_{i}.scpt')
    except:
        pass

print('')
print(f'✅ 成功添加: {added} 筆')
print(f'⚠️ 失敗: {len(failed)} 筆')
if failed:
    print(f'   失敗列表: {failed}')
print('')
print('設置摘要:')
print('  • 事件類型: 全天事件 (All-day)')
print('  • 提醒日期: 到期前28天')
print('  • 重複: 每年自動重複')
