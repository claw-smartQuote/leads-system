"""
FastAPI 汽車保險潛客系統 - 簡化版
"""
import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="汽車保險潛客系統", version="1.0.0")

# 設定
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 確保 static 資料夾存在
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ============ 保險客戶資料 (記憶體儲存) ============
leads_db = []

# ============ 路由 ============

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    """顯示潛客填寫表單"""
    return templates.TemplateResponse("form.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理後台"""
    new_count = len([l for l in leads_db if l.get("status") == "新"])
    
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
            .btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }}
            .btn-primary {{ background: #667eea; color: white; }}
            .actions {{ margin: 20px 0; }}
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
                <a href="/" target="_blank" class="btn btn-primary">🌐 查看表單</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>編號</th>
                        <th>姓名</th>
                        <th>電話</th>
                        <th>車牌</th>
                        <th>車型</th>
                        <th>查詢類型</th>
                        <th>狀態</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, lead in enumerate(leads_db, 1):
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{lead.get('name', '-')}</td>
                        <td>{lead.get('phone', '-')}</td>
                        <td>{lead.get('car_plate', '-')}</td>
                        <td>{lead.get('car_model', '-')}</td>
                        <td>{lead.get('inquiry_type', '-')}</td>
                        <td>{lead.get('status', '新')}</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/api/lead")
async def create_lead(request: Request):
    """接收潛客資料"""
    form = await request.form()
    lead = {
        "name": form.get("name"),
        "phone": form.get("phone"),
        "email": form.get("email"),
        "car_plate": form.get("car_plate"),
        "car_model": form.get("car_model"),
        "car_year": form.get("car_year"),
        "current_insurer": form.get("current_insurer"),
        "expiry_date": form.get("expiry_date"),
        "inquiry_type": form.get("inquiry_type"),
        "notes": form.get("notes"),
        "status": "新",
        "created_at": datetime.now().isoformat()
    }
    leads_db.append(lead)
    return {"success": True, "message": "資料已收到"}

@app.get("/api/leads")
async def get_leads():
    """獲取所有潛客"""
    return {"leads": leads_db, "total": len(leads_db)}

@app.get("/health")
async def health():
    return {"status": "ok", "leads_count": len(leads_db)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動汽車保險潛客系統...")
    print("📋 表單: http://localhost:8000/")
    print("⚙️ 管理後台: http://localhost:8000/admin")
    uvicorn.run(app, host="0.0.0.0", port=8000)
