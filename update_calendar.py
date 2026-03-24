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

# 首先刪除舊事件
print('正在清除舊事件...')
script_clear = '''
tell application "Calendar"
    tell calendar "港車北上保單"
        set allEvents to every event
        set eventCount to count of allEvents
        repeat with i from 1 to eventCount
            try
                delete item 1 of every event
            end try
        end repeat
        return "已清除"
    end tell
end tell
'''
subprocess.run(['osascript', '-e', script_clear], capture_output=True)
print('✅ 舊事件已清除')
print('')

# 添加新的事件（全天事件 + 28天前提醒）
print('正在創建新的全天事件...')
current_year = datetime.now().year
added_count = 0

for policy in allianz_policies:
    try:
        expiry_date = policy['expiry_date']
        plate = policy['plate_number']
        insured = policy['insured_name']
        
        # 提取月份和日期
        date_parts = expiry_date.split('-')
        month = date_parts[1]
        day = date_parts[2]
        
        # 計算提醒日期（到期前28天）
        expiry_this_year = datetime(current_year, int(month), int(day))
        alarm_date = expiry_this_year - timedelta(days=28)
        
        # AppleScript 創建全天事件
        script = f'''
tell application "Calendar"
    tell calendar "港車北上保單"
        set eventDate to date "{month}/{day}/{current_year}"
        set newEvent to make new event with properties {{
            summary:"🚗 保單到期: {plate}",
            start date:eventDate,
            end date:eventDate,
            allday event:true,
            description:"被保人: {insured}\\n車牌: {plate}\\n到期日: {month}/{day}\\n保險公司: 永誠\\n\\n⚠️ 提醒：到期前28天"
        }}
        -- 設置每年重複
        set recurrence of newEvent to "FREQ=YEARLY;INTERVAL=1"
        -- 添加28天前提醒
        set alarmDate to date "{alarm_date.strftime('%m/%d/%Y')} 09:00:00"
        make new display alarm at newEvent with properties {{trigger date:alarmDate}}
    end tell
end tell
'''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            added_count += 1
            if added_count % 10 == 0:
                print(f'  已添加 {added_count}/{len(allianz_policies)}...')
        else:
            print(f'  ❌ {plate}')
            
    except Exception as e:
        print(f'  ❌ 錯誤: {plate}')

print('')
print(f'✅ 成功添加 {added_count} 筆全天事件')
print('')
print('📅 新設置:')
print('  • 事件類型: 全天事件 (All-day)')
print('  • 提醒時間: 到期前28天上午9:00')
print('  • 重複頻率: 每年自動重複')

# 更新數據庫
for policy in data['policies']:
    if policy['insurer'] == '永城':
        policy['calendar_added'] = True
        policy['calendar_name'] = '港車北上保單'
        policy['calendar_allday'] = True
        policy['calendar_alarm_days'] = 28

with open('/Users/claw/.openclaw/workspace/memory/policies.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('')
print('✅ 數據庫已更新')
