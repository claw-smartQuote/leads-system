"""
FastAPI 汽車保險潛客系統 - 極簡版
"""
from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
from pathlib import Path

app = FastAPI()
BASE_DIR = Path(__file__).parent

# 管理員密碼（生產環境建議改為環境變量）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "smartquote2026"

# 記憶體資料庫
leads_db = []

def verify_admin(credentials: HTTPBasicCredentials):
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        return True
    return False

# 讀取 HTML 模板
def read_html(filename):
    filepath = BASE_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding='utf-8')
    return "<h1>File not found</h1>"

@app.get("/")
async def root():
    """首頁"""
    return HTMLResponse(content=read_html("templates/form.html"))

@app.get("/admin")
async def admin(credentials: HTTPBasicCredentials = Depends(security)):
    """管理後台 - 需要登入"""
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        return HTMLResponse(
            headers={"WWW-Authenticate": "Basic realm=\"管理後台\""},
            content="""<!DOCTYPE html><html><head><title>需要登入</title></head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#f5f5f5;">
            <div style="text-align:center; padding:40px; background:white; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color:#1a365d;">🔐 管理後台</h2>
                <p style="color:#666;">請輸入管理員帳號密碼</p>
            </div>
            </body></html>""",
            status_code=401
        )
    
    new_count = len([l for l in leads_db if l.get("status") == "新"])
    
    rows = ""
    for i, lead in enumerate(leads_db, 1):
        rows += f"""
        <tr data-id="{i}">
            <td>{i}</td>
            <td>{lead.get('name', '-')}</td>
            <td>{lead.get('phone', '-')}</td>
            <td>{lead.get('email', '-')}</td>
            <td>{lead.get('car_plate', '-')}</td>
            <td>{lead.get('car_model', '-')}</td>
            <td>{lead.get('expiry_date', '-')}</td>
            <td>{lead.get('inquiry_type', '-')}</td>
            <td><span class="status status-{lead.get('status', '新').lower()}">{lead.get('status', '新')}</span></td>
            <td>
                <button class="btn-view" onclick="viewLead({i})">查看</button>
                <button class="btn-delete" onclick="deleteLead({i})">刪除</button>
            </td>
        </tr>
        """
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>潛客管理後台</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; text-align: center; }}
        .stat-box h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
        .stat-box .number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #667eea; color: white; font-weight: 500; }}
        tr:hover {{ background: #f9f9f9; }}
        .btn {{ padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-right: 5px; }}
        .btn-view {{ background: #667eea; color: white; }}
        .btn-delete {{ background: #dc3545; color: white; }}
        .status {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        .status-新 {{ background: #e3f2fd; color: #1976d2; }}
        .status-已聯繫 {{ background: #fff3e0; color: #f57c00; }}
        .status-已報價 {{ background: #f3e5f5; color: #7b1fa2; }}
        .status-完成 {{ background: #e8f5e9; color: #388e3c; }}
        .actions {{ margin: 20px 0; display: flex; gap: 10px; }}
        .btn-action {{ padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }}
        .btn-primary {{ background: #667eea; color: white; }}
        .btn-export {{ background: #28a745; color: white; }}
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }}
        .modal-content {{ background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 100px auto; }}
        .modal h2 {{ margin-top: 0; }}
        .modal-close {{ float: right; cursor: pointer; font-size: 24px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 潛客管理後台</h1>
        <div class="stats">
            <div class="stat-box">
                <h3>總潛客數</h3>
                <div class="number">{len(leads_db)}</div>
            </div>
            <div class="stat-box">
                <h3>新潛客</h3>
                <div class="number">{new_count}</div>
            </div>
        </div>
        <div class="actions">
            <a href="/" target="_blank" class="btn-action btn-primary">🌐 查看表單</a>
            <button class="btn-action btn-export" onclick="exportData()">📊 匯出 Excel</button>
        </div>
        <table>
            <thead>
                <tr>
                    <th>編號</th>
                    <th>姓名</th>
                    <th>電話</th>
                    <th>電郵/微信</th>
                    <th>車牌</th>
                    <th>車型</th>
                    <th>到期日</th>
                    <th>查詢類型</th>
                    <th>狀態</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {rows if rows else '<tr><td colspan="10" style="text-align:center;color:#999;">暫無資料</td></tr>'}
            </tbody>
        </table>
    </div>
    
    <!-- Modal for viewing details -->
    <div id="leadModal" class="modal">
        <div class="modal-content">
            <span class="modal-close" onclick="closeModal()">&times;</span>
            <h2>潛客詳細資料</h2>
            <div id="leadDetails"></div>
        </div>
    </div>
    
    <script>
        let leads = {leads_db};
        
        function viewLead(id) {{
            const lead = leads[id - 1];
            if (!lead) return;
            
            let html = '<table style="width:100%;">';
            for (let [key, value] of Object.entries(lead)) {{
                if (value) {{
                    html += '<tr><td style="padding:8px;border-bottom:1px solid #eee;"><strong>' + key + ':</strong></td><td style="padding:8px;border-bottom:1px solid #eee;">' + value + '</td></tr>';
                }}
            }}
            html += '</table>';
            
            document.getElementById('leadDetails').innerHTML = html;
            document.getElementById('leadModal').style.display = 'block';
        }}
        
        function deleteLead(id) {{
            if (!confirm('確定要刪除這筆記錄嗎？')) return;
            fetch('/api/leads/' + (id - 1), {{ method: 'DELETE' }})
                .then(function(response) {{ return response.json(); }})
                .then(function(data) {{
                    if (data.success) {{
                        alert('已刪除');
                        location.reload();
                    }} else {{
                        alert('刪除失敗: ' + (data.error || '未知錯誤'));
                    }}
                }})
                .catch(function(e) {{
                    alert('刪除失敗: ' + e);
                }});
        }}
        
        function closeModal() {{
            document.getElementById('leadModal').style.display = 'none';
        }}
        
        function exportData() {{
            window.open('/api/leads/excel', '_blank');
        }}
        
        window.onclick = function(event) {{
            if (event.target == document.getElementById('leadModal')) {{
                closeModal();
            }}
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

@app.get("/terms")
async def terms():
    """免責條款及私隱條款"""
    html = """
<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>免責條款及私隱條款 - 汽車保險到期提示及報價服務</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #a0aec0;
            --accent-light: #c0c0c0;
            --bg-light: #f7fafc;
            --text-dark: #1a202c;
            --text-muted: #718096;
            --border: #e2e8f0;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(180deg, #1a365d 0%, #2c5282 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            overflow: hidden;
        }
        .header {
            background: var(--primary);
            color: white;
            padding: 35px 30px;
            text-align: center;
            position: relative;
        }
        .header::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--accent);
        }
        .header h1 { font-size: 26px; font-weight: 700; margin-bottom: 10px; letter-spacing: 1px; }
        .header p { opacity: 0.9; }
        .content { padding: 40px; }
        .section { margin-bottom: 35px; }
        .section h2 {
            color: var(--primary);
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 3px solid var(--accent);
            display: flex;
            align-items: center;
        }
        .section h2 .num {
            background: var(--accent);
            color: var(--primary);
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            margin-right: 12px;
            font-weight: 700;
        }
        .section h3 { color: var(--text-dark); font-size: 16px; margin: 20px 0 12px; font-weight: 600; }
        .section p { color: var(--text-muted); line-height: 1.8; margin-bottom: 15px; font-size: 14px; }
        .section ul { color: var(--text-muted); line-height: 2; margin-left: 20px; font-size: 14px; }
        .highlight {
            background: #fffaf0;
            padding: 18px;
            border-radius: 10px;
            border-left: 4px solid var(--accent);
            margin: 20px 0;
        }
        .highlight p { margin-bottom: 0; color: #92400e; font-weight: 500; }
        .back-btn {
            display: inline-block;
            padding: 14px 35px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            letter-spacing: 1px;
        }
        .back-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(26, 54, 93, 0.3); }
        .footer {
            text-align: center;
            padding: 25px 20px;
            color: var(--text-muted);
            font-size: 12px;
            background: var(--bg-light);
            border-top: 1px solid var(--border);
        }
        .contact { color: var(--primary); text-decoration: none; font-weight: 500; }
        .contact:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>免責條款及私隱條款</h1>
            <p>汽車保險到期提示及報價服務</p>
        </div>
        <div class="content">
            <div class="section">
                <h2><span class="num">一</span>免責條款</h2>
                
                <h3>1. 服務性質</h3>
                <p>本服務只作為資訊平台，提供的保險報價及到期提示僅供參考，不構成任何保險建議或要約邀請。</p>
                
                <h3>2. 非保險中介</h3>
                <p>本服務並非保險中介人或保險公司，所有報價均由第三方保險公司或其代理提供。本服務不對任何保險公司的產品、報價或決定負責。</p>
                
                <h3>3. 資料準確性</h3>
                <p>本服務盡力確保提供準確資訊，但無法保證所有資料完整無誤。最終保費及承保條款以保險公司正式回覆為準。</p>
                
                <h3>4. 第三方連結</h3>
                <p>本服務可能包含第三方網站連結，這些網站的內容及私隱慣例不在本服務控制範圍內。</p>
                
                <div class="highlight">
                    <p><strong>⚠️ 重要提示：</strong><br>
                    用戶使用此服務代表同意自行承擔風險。<br>
                    就所有不可抗力因素（包括但不限於天災、網絡故障、系統中斷等），本服務不承擔任何責任。</p>
                </div>
            </div>
            
            <div class="section">
                <h2><span class="num">二</span>私隱條款</h2>
                
                <h3>1. 收集資料</h3>
                <p>本服務收集的個人資料（包括姓名、電話、電郵、車牌及車型）只用於提供保險報價服務及到期提示，不會用於任何其他用途。</p>
                
                <h3>2. 資料保密</h3>
                <p>所有個人資料均保密處理，不會出售或轉讓予任何第三方（法律規定除外）。</p>
                
                <h3>3. 資料用途</h3>
                <ul>
                    <li>提供保險報價比較</li>
                    <li>發送到期提示通知</li>
                    <li>改善服務質素</li>
                </ul>
                
                <h3>4. 資料保存及刪除</h3>
                <p>用戶可隨時要求刪除個人資料，請聯絡：<a href="mailto:ai@smartquote.cn" class="contact">ai@smartquote.cn</a></p>
                
                <h3>5. Cookies</h3>
                <p>本服務使用 cookies 提升用戶體驗，用戶可透過瀏覽器設定拒絕 cookies。</p>
                
                <div class="highlight">
                    <p><strong>⚠️ 重要提示：</strong><br>
                    用戶使用此服務代表同意自行承擔風險。<br>
                    就所有不可抗力因素（包括但不限於天災、網絡故障、系統中斷等），本服務不承擔任何責任。</p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="/" class="back-btn">← 返回首頁</a>
            </div>
        </div>
        <div class="footer">
            最後更新日期：2026年4月8日<br>
            查詢電郵：<a href="mailto:ai@smartquote.cn" class="contact">ai@smartquote.cn</a>
        </div>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html)

@app.post("/api/leads")
async def create_lead(request: Request):
    """接收潛客資料"""
    try:
        body = await request.body()
        import json
        data = json.loads(body)
        lead = {
            "name": data.get("name"),
            "phone": data.get("phone"),
            "email": data.get("email"),
            "car_plate": data.get("car_plate"),
            "car_model": data.get("car_model"),
            "car_year": data.get("car_year"),
            "current_insurer": data.get("current_insurer"),
            "expiry_date": data.get("expiry_date"),
            "inquiry_type": data.get("inquiry_type"),
            "notes": data.get("notes"),
            "status": "新"
        }
        leads_db.append(lead)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/leads")
async def get_leads(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return {"leads": leads_db, "total": len(leads_db)}

@app.get("/api/leads/excel")
async def export_leads_excel(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    """導出 Excel 文件"""
    import tempfile
    import pandas as pd
    from datetime import datetime
    from fastapi.responses import FileResponse
    
    if not leads_db:
        return JSONResponse({"error": "No data"}, status_code=404)
    
    # 創建臨時文件
    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    df = pd.DataFrame(leads_db)
    df.to_excel(temp_path, index=False, engine='openpyxl')
    
    filename = f"潛客資料_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return FileResponse(
        temp_path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=filename
    )

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: int, credentials: HTTPBasicCredentials = Depends(security)):
    """刪除指定潛客"""
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        if 0 <= lead_id < len(leads_db):
            deleted = leads_db.pop(lead_id)
            return JSONResponse({"success": True, "deleted": deleted})
        else:
            return JSONResponse({"success": False, "error": "Record not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動系統...")
    print("📋 http://localhost:8000/")
    print("⚙️ http://localhost:8000/admin")
    uvicorn.run(app, host="0.0.0.0", port=8000)
