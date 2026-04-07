"""
FastAPI 汽車保險潛客系統 - 極簡版
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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
        <tr>
            <td>{i}</td>
            <td>{lead.get('name', '-')}</td>
            <td>{lead.get('phone', '-')}</td>
            <td>{lead.get('car_plate', '-')}</td>
            <td>{lead.get('inquiry_type', '-')}</td>
            <td>{lead.get('status', '新')}</td>
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
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; text-align: center; }}
        .stat-box h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
        .stat-box .number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #667eea; color: white; font-weight: 500; }}
        tr:hover {{ background: #f9f9f9; }}
        .btn {{ padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; text-decoration: none; display: inline-block; }}
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
        <div style="margin: 20px 0;">
            <a href="/" class="btn">🌐 查看表單</a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>編號</th>
                    <th>姓名</th>
                    <th>電話</th>
                    <th>車牌</th>
                    <th>查詢類型</th>
                    <th>狀態</th>
                </tr>
            </thead>
            <tbody>
                {rows if rows else '<tr><td colspan="6" style="text-align:center;color:#999;">暫無資料</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html)

@app.post("/api/leads")
async def create_lead(request: Request):
    """接收潛客資料"""
    form = await request.form()
    lead = {
        "name": form.get("name"),
        "phone": form.get("phone"),
        "email": form.get("email"),
        "car_plate": form.get("car_plate"),
        "car_model": form.get("car_model"),
        "inquiry_type": form.get("inquiry_type"),
        "status": "新"
    }
    leads_db.append(lead)
    return {"success": True}

@app.get("/api/leads")
async def get_leads():
    return {"leads": leads_db, "total": len(leads_db)}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動系統...")
    print("📋 http://localhost:8000/")
    print("⚙️ http://localhost:8000/admin")
    uvicorn.run(app, host="0.0.0.0", port=8000)
