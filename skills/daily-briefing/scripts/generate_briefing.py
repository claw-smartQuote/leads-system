#!/usr/bin/env python3
"""
每日晨報生成器 (廣東話版)
生成語音晨報內容，包括：
- 問候語
- 日期與天氣
- 保單到期提醒
- 待辦事項
- 潛客系統提示
- 今日重點

注意：此腳本生成廣東話（粵語）內容，需配合廣東話 TTS 語音使用
"""

import json
import csv
from datetime import datetime, timedelta
import os
import requests
import glob

# 天氣描述翻譯表（簡體中文 → 廣東話）
WEATHER_TRANSLATIONS = {
    '周边有零星小雨': '附近有零星小雨',
    '周边有雨': '附近有雨',
    '局部多云': '局部多雲',
    '多云': '多雲',
    '晴朗': '晴朗',
    '晴': '晴天',
    '小雨': '小雨',
    '中雨': '中雨',
    '大雨': '大雨',
    '阵雨': '陣雨',
    '雷阵雨': '雷陣雨',
    '阴天': '陰天',
    '阴': '陰天',
    '雾': '大霧',
    '薄雾': '薄霧',
    '霾': '煙霞',
    '有风': '有風',
    '大风': '大風',
    '暴风雨': '暴風雨',
    '雪': '落雪',
    '小雪': '小雪',
    '大雪': '大雪',
    '雨夹雪': '雨夾雪',
    '冰雹': '落冰雹',
    'Clear': '晴朗',
    'Sunny': '晴天',
    'Partly cloudy': '局部多雲',
    'Cloudy': '多雲',
    'Overcast': '陰天',
    'Rain': '有雨',
    'Light rain': '小雨',
    'Heavy rain': '大雨',
    'Patchy rain nearby': '附近有零星小雨',
    'Patchy rain possible': '可能有零星小雨',
    'Mist': '薄霧',
    'Fog': '大霧',
}

def translate_weather_desc(desc):
    """將天氣描述翻譯為廣東話"""
    if not desc:
        return '天氣不詳'
    # 先嘗試直接翻譯
    if desc in WEATHER_TRANSLATIONS:
        return WEATHER_TRANSLATIONS[desc]
    # 如果找不到，返回原文（可能已經是中文）
    return desc

def get_today_info():
    """獲取今日日期資訊"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    
    return {
        "date": now.strftime("%Y年%m月%d日"),
        "weekday": weekday,
        "time": now.strftime("%H:%M")
    }

def get_weather():
    """獲取香港天氣預報"""
    try:
        # 使用 wttr.in API 獲取香港天氣
        url = "https://wttr.in/Hong+Kong?format=j1&lang=zh"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data['current_condition'][0]
        today = data['weather'][0]
        
        # 獲取當前溫度和天氣描述（轉換為廣東話）
        temp_c = current['temp_C']
        raw_desc = current['lang_zh'][0]['value'] if 'lang_zh' in current else current['weatherDesc'][0]['value']
        desc = translate_weather_desc(raw_desc)
        
        # 獲取今日最高/最低溫度
        max_temp = today['maxtempC']
        min_temp = today['mintempC']
        
        # 獲取降雨機率
        chance_of_rain = today['hourly'][4]['chanceofrain'] if 'hourly' in today and len(today['hourly']) > 4 else "0"
        
        return {
            'temp': temp_c,
            'desc': desc,
            'max_temp': max_temp,
            'min_temp': min_temp,
            'rain_chance': chance_of_rain
        }
    except Exception as e:
        print(f"獲取天氣錯誤: {e}")
        return None

def get_pending_tasks():
    """獲取待辦事項"""
    reminders_file = os.path.expanduser("~/.openclaw/workspace/memory/personal_reminders.json")
    tasks = []
    
    try:
        with open(reminders_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        today = datetime.now().date()
        
        # 檢查即將到期的帳戶
        for account in data.get('accounts', []):
            due_date = datetime.strptime(account['due_date'], '%Y-%m-%d').date()
            days_until = (due_date - today).days
            
            if 0 <= days_until <= 7:
                tasks.append({
                    'type': '帳戶到期',
                    'name': account['name'],
                    'days': days_until
                })
                
    except Exception as e:
        print(f"讀取提醒資料錯誤: {e}")
    
    return tasks

def get_todo_list():
    """獲取待辦清單（從 todo 文件）"""
    todo_file = os.path.expanduser("~/.openclaw/workspace/memory/todo.json")
    todos = []
    
    try:
        if os.path.exists(todo_file):
            with open(todo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            today = datetime.now().date()
            
            for item in data.get('todos', []):
                if not item.get('completed', False):
                    due_date_str = item.get('due_date')
                    if due_date_str:
                        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                        days_until = (due_date - today).days
                        if days_until <= 3:  # 只顯示3天內的待辦
                            todos.append({
                                'task': item['task'],
                                'days': days_until,
                                'priority': item.get('priority', 'normal')
                            })
                    else:
                        # 無截止日期的待辦
                        todos.append({
                            'task': item['task'],
                            'days': None,
                            'priority': item.get('priority', 'normal')
                        })
    except Exception as e:
        print(f"讀取待辦清單錯誤: {e}")
    
    # 如果沒有 JSON 文件，檢查 MEMORY.md 中的待辦
    if not todos:
        memory_file = os.path.expanduser("~/.openclaw/workspace/MEMORY.md")
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找待辦清單部分
                if '## 🎯 待學習/改進項目' in content:
                    section = content.split('## 🎯 待學習/改進項目')[1].split('---')[0]
                    for line in section.split('\n'):
                        if line.strip().startswith('- [ ]'):
                            task = line.replace('- [ ]', '').strip()
                            if task:
                                todos.append({
                                    'task': task,
                                    'days': None,
                                    'priority': 'normal'
                                })
        except Exception as e:
            print(f"從 MEMORY.md 讀取待辦錯誤: {e}")
    
    return todos

def get_leads_summary():
    """獲取昨日潛客數據摘要"""
    try:
        desktop_path = os.path.expanduser("~/Desktop/潛客系統")
        if not os.path.exists(desktop_path):
            return None
            
        # 查找昨日檔案
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        
        excel_files = glob.glob(os.path.join(desktop_path, f"*{yesterday}*.xlsx"))
        
        if excel_files:
            # 這裡可以讀取 Excel 計算數量，現在只返回有文件
            return len(excel_files)
        
        return 0
    except Exception as e:
        print(f"獲取潛客摘要錯誤: {e}")
        return None

def check_expiring_policies(days=14):
    """檢查即將到期的保單"""
    policies_file = os.path.expanduser("~/.openclaw/workspace/memory/policies.json")
    expiring = []
    
    try:
        with open(policies_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            policies = data.get('policies', [])
            
        today = datetime.now()
        
        for policy in policies:
            try:
                # 假設 expiry_date 格式為 YYYY-MM-DD
                expiry = datetime.strptime(policy['expiry_date'], '%Y-%m-%d')
                # 將過期日期調整到當年
                expiry = expiry.replace(year=today.year)
                
                days_until = (expiry - today).days
                if 0 <= days_until <= days:
                    expiring.append({
                        'plate': policy['plate_number'],
                        'name': policy['insured_name'],
                        'days': days_until
                    })
            except:
                continue
                
    except Exception as e:
        print(f"讀取保單資料錯誤: {e}")
    
    return expiring

def generate_briefing():
    """生成晨報內容"""
    info = get_today_info()
    weather = get_weather()
    expiring_policies = check_expiring_policies()
    pending_tasks = get_pending_tasks()
    todos = get_todo_list()
    leads_count = get_leads_summary()
    
    # 根據時間生成問候語
    hour = datetime.now().hour
    if hour < 11:
        greeting = "早晨"
    elif hour < 14:
        greeting = "午安"
    else:
        greeting = "你好"
    
    # 構建報告內容
    parts = []
    parts.append(f"{greeting}！呢度係 AI小龍蝦 每日晨報。")
    parts.append(f"今日係 {info['date']}，{info['weekday']}。")
    
    # 天氣預報
    if weather:
        parts.append(f"天氣預報：香港今日{weather['desc']}，氣溫{weather['min_temp']}至{weather['max_temp']}度，現時{weather['temp']}度。")
        if int(weather['rain_chance']) > 50:
            parts.append(f"降雨機率{weather['rain_chance']} percent，記得帶遮。")
    else:
        parts.append("天氣預報：暫時無法獲取天氣資訊。")
    
    # 待辦清單
    all_tasks = []
    all_tasks.extend([{'task': f"{t['name']}（帳戶到期）", 'days': t['days'], 'priority': 'high'} for t in pending_tasks])
    all_tasks.extend(todos)
    
    if all_tasks:
        parts.append(f"待辦清單：你有 {len(all_tasks)} 項待辦事項。")
        # 只顯示前3項
        for task in all_tasks[:3]:
            if task.get('days') is not None and task['days'] >= 0:
                if task['days'] == 0:
                    parts.append(f"今日到期：{task['task']}。")
                else:
                    parts.append(f"{task['task']}，仲有 {task['days']} 日。")
            else:
                parts.append(f"{task['task']}。")
        if len(all_tasks) > 3:
            parts.append(f"仲有 {len(all_tasks) - 3} 項待辦，詳情請查看待辦清單。")
    else:
        parts.append("待辦清單：今日暫無待辦事項，輕鬆一日。")
    
    # 保單提醒
    if expiring_policies:
        parts.append(f"保單提醒：有 {len(expiring_policies)} 份保單即將到期。")
        for policy in expiring_policies[:3]:  # 最多報告 3 份
            if policy['days'] == 0:
                parts.append(f"車牌 {policy['plate']}，被保人 {policy['name']}，今日到期。")
            else:
                parts.append(f"車牌 {policy['plate']}，被保人 {policy['name']}，{policy['days']} 日後到期。")
    else:
        parts.append("保單狀況：未來兩星期內沒有即將到期嘅保單。")
    
    # 潛客系統提示
    if leads_count:
        parts.append(f"潛客系統：昨日有 {leads_count} 個潛客資料檔案，記得檢查。")
    else:
        parts.append("潛客系統：記得檢查桌面『潛客系統』文件夾嘅最新資料。")
    
    # 結語
    parts.append("祝你今日工作順利，有需要隨時搵我！")
    
    return " ".join(parts)

if __name__ == "__main__":
    briefing = generate_briefing()
    print(briefing)
