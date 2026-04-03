#!/usr/bin/env python3
"""將 28car 爬蟲數據同步到 Render 潛客系統"""

import sqlite3
import urllib.request
import json
import time
from pathlib import Path

RENDER_API = "https://leads-system.onrender.com/api/leads"
CAR28_DB = Path('/Users/claw/.openclaw/workspace/car28_scraper.db')

def get_28car_leads():
    conn = sqlite3.connect(str(CAR28_DB))
    c = conn.cursor()
    c.execute('SELECT phone, email, model, description, source, created_at FROM car28_leads')
    rows = c.fetchall()
    conn.close()
    return rows

def push_lead(lead_data):
    """推送單個潛客到 Render API"""
    try:
        # 從 model 描述中提取車型（取第一行或前半部分）
        model_raw = lead_data[2] or ''
        car_model = model_raw.split('\xa0')[0].strip() if model_raw else None
        
        # 構造 API 數據
        payload = {
            "name": "28car訪客",
            "phone": lead_data[0],
            "email": lead_data[1] or None,
            "car_model": car_model,
            "inquiry_type": "28car爬蟲",
            "notes": f"來源：{lead_data[4]} | 時間：{lead_data[5]}"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            RENDER_API,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, payload["phone"]
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:100]}"
    except Exception as e:
        return False, str(e)

def main():
    leads = get_28car_leads()
    print(f"📦 找到 {len(leads)} 條 28car 記錄")
    
    success = 0
    failed = 0
    
    for i, lead in enumerate(leads, 1):
        ok, result = push_lead(lead)
        if ok:
            success += 1
            print(f"  ✅ [{i}/{len(leads)}] {result}")
        else:
            failed += 1
            print(f"  ❌ [{i}/{len(leads)}] {lead[0]}: {result}")
        
        if i % 10 == 0:
            print(f"  📊 進度: {i}/{len(leads)}")
        
        time.sleep(0.3)  # 避免太快
    
    print(f"\n✅ 完成！成功: {success}, 失敗: {failed}")

if __name__ == '__main__':
    main()
