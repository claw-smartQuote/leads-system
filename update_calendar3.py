#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timedelta
import os

# 讀取保單數據
with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'r') as f:
    data = json.load(f)

# 篩選永誠保險的保單
allianz_policies = [p for p in data['policies'] if p['insurer'] == '永城']

print(f'找到 {len(allianz_policies)} 筆永誠保險保單')
print('')
print('正在創建全天提醒事件（到期前28天）...')
print('')

current_year = datetime.now().year
added_count = 0
failed = []

for i, policy in enumerate(allianz_policies):
    try:
        expiry_date = policy['expiry_date']
        plate = policy['plate_number']
        insured = policy['insured_name']
        
        # 提取月份和日期
        date_parts = expiry_date.split('-')
        month = int(date_parts[1])
        day = int(date_parts[2])
        
        # 計算提醒日期（到期前28天）
        expiry_this_year = datetime(current_year, month, day)
        reminder_date = expiry_this_year - timedelta(days=28)
        
        r_month = reminder_date.month
        r_day = reminder_date.day
        
        # 創建 AppleScript 文件
        script_content = f'''tell application "Calendar"
tell calendar "港車北上保單"
set startDate to date "{r_month}/{r_day}/{current_year}"
set newEvent to make new event with properties {{summary:"🚗 保單到期提醒: {plate}", start date:startDate, allday event:true, description:"被保人: {insured} | 車牌: {plate} | 保單到期日: {month}/{day} | 保險公司: 永誠"}}
set recurrence of newEvent to "FREQ=YEARLY;INTERVAL=1"
end tell
end tell'''
        
        script_file = f'/tmp/calendar_event_{i}.scpt'
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # 執行腳本
        result = subprocess.run(['osascript', script_file], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            added_count += 1
        else:
            failed.append(plate)
            
        # 清理臨時文件
        os.remove(script_file)
        
        if (i + 1) % 10 == 0:
            print(f'  進度: {i + 1}/{len(allianz_policies)}')
            
    except Exception as e:
        failed.append(policy.get('plate_number', 'unknown'))

print('')
print(f'✅ 成功添加 {added_count} 筆全天提醒事件')
if failed:
    print(f'⚠️ 失敗: {len(failed)} 筆')
print('')
print('📅 設置說明:')
print('  • 事件類型: 全天事件 (All-day)')
print('  • 提醒日期: 到期前28天')
print('  • 重複頻率: 每年自動重複')
print('')
print('例如:')
print('  • 保單到期 6/11 → 提醒設置在 5/14')
print('  • 保單到期 11/19 → 提醒設置在 10/22')

# 更新數據庫
for policy in data['policies']:
    if policy['insurer'] == '永城':
        policy['calendar_added'] = True
        policy['calendar_name'] = '港車北上保單'
        policy['calendar_allday'] = True
        policy['calendar_reminder_days_before'] = 28

with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('')
print('✅ 數據庫已更新')
