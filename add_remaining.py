#!/usr/bin/env python3
import json
import subprocess
import time
from datetime import datetime, timedelta

with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'r') as f:
    data = json.load(f)

allianz_policies = [p for p in data['policies'] if p['insurer'] == '永城']

# 失敗的車牌列表
failed_plates = ['UR855', 'UF1276', 'RN6534', 'KM1322', 'XY6833', 'RV9128', 'AA398', 
    'DG2688', 'XXLAMXX', 'LA293', 'EV0F', 'WH3293', 'WD1962', 'YP4456',
    'ZJ7522', 'VX8331', 'WJ1948', 'TC821', 'TB9355', 'XF3610', 'UD8289',
    'YP5424', 'WH6291', 'TJ9331', 'XH2722', 'ZL4085', 'VR8533', 'TY3014',
    'WP6812', 'MU986']

current_year = datetime.now().year
month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']

added = 0
still_failed = []

print(f'使用新方法添加 {len(failed_plates)} 筆保單...')
print('')

for policy in allianz_policies:
    if policy['plate_number'] not in failed_plates:
        continue
        
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
        month_name = month_names[r_month]
        
        # 使用新方式構建日期
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
set newEvent to make new event with properties {{summary:"🚗 保單到期提醒: {plate}", start date:startDate, end date:endDate, allday event:true, description:"被保人: {insured} | 車牌: {plate} | 到期日: {month}/{day} | 永誠"}}
set recurrence of newEvent to "FREQ=YEARLY;INTERVAL=1"
end tell
end tell"""
        
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=20)
        
        if result.returncode == 0:
            added += 1
            print(f'✅ {plate}')
        else:
            still_failed.append(plate)
            print(f'❌ {plate}')
            
        time.sleep(0.3)
            
    except Exception as e:
        still_failed.append(policy['plate_number'])
        print(f'⚠️ {policy["plate_number"]}')

print('')
print(f'本次成功添加: {added} 筆')
print(f'仍然失敗: {len(still_failed)} 筆')
