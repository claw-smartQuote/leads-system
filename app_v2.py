"""
FastAPI 汽車保險潛客系統 - 極簡版
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
from pathlib import Path

app = FastAPI()
BASE_DIR = Path(__file__).parent

# 記憶體資料庫
leads_db = []

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
async def admin():
    """管理後台"""
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
async def get_leads():
    return {"leads": leads_db, "total": len(leads_db)}

@app.get("/api/leads/excel")
async def export_leads_excel():
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
async def delete_lead(lead_id: int):
    """刪除指定潛客"""
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
