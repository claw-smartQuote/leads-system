#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timedelta

# 讀取保單數據
with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'r') as f:
    data = json.load(f)

# 篩選永誠保險的保單
allianz_policies = [p for p in data['policies'] if p['insurer'] == '永城']

print(f'找到 {len(allianz_policies)} 筆永誠保險保單')
print('')

# 簡化方法：直接在到期前28天創建全天提醒事件
print('正在創建全天提醒事件（到期前28天）...')
current_year = datetime.now().year
added_count = 0

for policy in allianz_policies:
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
        
        # 格式化日期
        r_month = reminder_date.month
        r_day = reminder_date.day
        
        # AppleScript 創建全天事件（簡化版）
        script = f'''
tell application "Calendar"
    tell calendar "港車北上保單"
        set startDate to date "{r_month}/{r_day}/{current_year}"
        set endDate to date "{r_month}/{r_day}/{current_year}"
        set newEvent to make new event with properties {{
            summary:"🚗 保單到期提醒: {plate}",
            start date:startDate,
            allday event:true,
            description:"被保人: {insured}\\n車牌: {plate}\\n保單到期日: {month}/{day}\\n保險公司: 永誠"
        }}
        set recurrence of newEvent to "FREQ=YEARLY;INTERVAL=1"
    end tell
end tell
'''
        
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            added_count += 1
            if added_count % 10 == 0:
                print(f'  已添加 {added_count}/{len(allianz_policies)}...')
        else:
            print(f'  ⚠️ {plate}: {result.stderr[:50]}')
            
    except Exception as e:
        print(f'  ⚠️ 錯誤: {plate} - {str(e)[:30]}')

print('')
print(f'✅ 成功添加 {added_count} 筆全天提醒事件')
print('')
print('📅 新設置:')
print('  • 事件類型: 全天事件 (All-day)')
print('  • 事件日期: 到期前28天')
print('  • 重複頻率: 每年自動重複')
print('')
print('例如:')
print('  • 保單到期 6月11日 → 提醒設置在 5月14日')
print('  • 保單到期 11月19日 → 提醒設置在 10月22日')

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
