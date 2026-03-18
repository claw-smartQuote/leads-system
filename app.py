"""
FastAPI 主程式 - 汽車保險潛客系統
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加項目目錄到路徑
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from database import Database
from export_excel import ExcelExporter
from whatsapp_notifier import WhatsAppNotifier

# 初始化 FastAPI
app = FastAPI(
    title="汽車保險潛客系統",
    description="收集潛在客戶資料並發送 WhatsApp 通知",
    version="1.0.0"
)

# 設定模板和靜態文件
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化組件
db = Database()
exporter = ExcelExporter()
notifier = WhatsAppNotifier()

# ============ 數據模型 ============

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    car_plate: Optional[str] = None
    car_model: Optional[str] = None
    car_year: Optional[str] = None
    current_insurer: Optional[str] = None
    expiry_date: Optional[str] = None
    inquiry_type: str
    notes: Optional[str] = None

class LeadResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    car_plate: Optional[str]
    car_model: Optional[str]
    car_year: Optional[str]
    current_insurer: Optional[str]
    expiry_date: Optional[str]
    inquiry_type: str
    notes: Optional[str]
    created_at: str
    status: str
    follow_up_date: Optional[str]

class StatusUpdate(BaseModel):
    status: str
    follow_up_date: Optional[str] = None

# ============ 前端路由 ============

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    """顯示潛客填寫表單"""
    return templates.TemplateResponse("form.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理後台（簡單版）"""
    leads = db.get_all_leads()
    new_count = db.get_new_leads_count()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>潛客管理後台</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ color: #333; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }}
            .stat-box h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
            .stat-box .number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
            table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #667eea; color: white; font-weight: 500; }}
            tr:hover {{ background: #f9f9f9; }}
            .status {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
            .status-new {{ background: #e3f2fd; color: #1976d2; }}
            .status-contacted {{ background: #fff3e0; color: #f57c00; }}
            .status-quoted {{ background: #f3e5f5; color: #7b1fa2; }}
            .status-won {{ background: #e8f5e9; color: #388e3c; }}
            .btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 5px; }}
            .btn-primary {{ background: #667eea; color: white; }}
            .btn-success {{ background: #4caf50; color: white; }}
            .btn-export {{ background: #ff9800; color: white; }}
            .actions {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 潛客管理後台</h1>
            
            <div class="stats">
                <div class="stat-box">
                    <h3>總潛客數</h3>
                    <div class="number">{len(leads)}</div>
                </div>
                <div class="stat-box">
                    <h3>新潛客</h3>
                    <div class="number">{new_count}</div>
                </div>
            </div>
            
            <div class="actions">
                <a href="/api/export" class="btn btn-export">📊 匯出 Excel</a>
                <a href="/" target="_blank" class="btn btn-primary">🌐 查看表單</a>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>編號</th>
                        <th>姓名</th>
                        <th>電話</th>
                        <th>車型</th>
                        <th>查詢類型</th>
                        <th>提交時間</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for lead in leads[:50]:  # 顯示最近 50 個
        status_class = "status-new"
        if lead['status'] == '已聯絡':
            status_class = "status-contacted"
        elif lead['status'] == '已報價':
            status_class = "status-quoted"
        elif lead['status'] == '已成交':
            status_class = "status-won"
        
        html_content += f"""
                    <tr>
                        <td>#{lead['id']}</td>
                        <td>{lead['name']}</td>
                        <td>{lead['phone']}</td>
                        <td>{lead.get('car_model', '-')}</td>
                        <td>{lead['inquiry_type']}</td>
                        <td>{lead['created_at'][:16]}</td>
                        <td><span class="status {status_class}">{lead['status']}</span></td>
                        <td>
                            <button class="btn btn-primary" onclick="updateStatus({lead['id']}, '已聯絡')">標記已聯絡</button>
                        </td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <script>
            async function updateStatus(id, status) {
                await fetch(`/api/leads/${id}/status`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({status: status})
                });
                location.reload();
            }
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

# ============ API 路由 ============

@app.post("/api/leads", response_model=dict)
async def create_lead(lead: LeadCreate):
    """創建新潛客"""
    try:
        # 轉換為字典
        lead_data = lead.dict()
        
        # 存入資料庫
        lead_id = db.add_lead(lead_data)
        
        # 發送 WhatsApp 通知
        try:
            notifier.send_new_lead_notification(lead_data, lead_id)
        except Exception as e:
            print(f"WhatsApp 通知發送失敗: {e}")
        
        return {
            "success": True,
            "message": "潛客資料已提交",
            "lead_id": lead_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leads", response_model=List[LeadResponse])
async def get_leads(status: Optional[str] = None, limit: Optional[int] = None):
    """獲取所有潛客"""
    leads = db.get_all_leads(status=status, limit=limit)
    return leads

@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int):
    """根據 ID 獲取潛客"""
    lead = db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="潛客不存在")
    return lead

@app.put("/api/leads/{lead_id}/status")
async def update_lead_status(lead_id: int, update: StatusUpdate):
    """更新潛客狀態"""
    db.update_status(lead_id, update.status, update.follow_up_date)
    return {"success": True, "message": "狀態已更新"}

@app.get("/api/export")
async def export_leads():
    """匯出所有潛客為 Excel"""
    leads = db.get_all_leads()
    filepath = exporter.export_all_leads(leads)
    return FileResponse(
        filepath,
        filename=Path(filepath).name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/api/export/daily")
async def export_daily_report():
    """匯出每日報表"""
    today = datetime.now().strftime('%Y-%m-%d')
    leads = db.get_leads_by_date_range(today, today)
    filepath = exporter.export_daily_report(leads, today)
    return FileResponse(
        filepath,
        filename=f"daily_report_{today}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/api/stats")
async def get_stats():
    """獲取統計數據"""
    total = len(db.get_all_leads())
    new = db.get_new_leads_count()
    
    return {
        "total_leads": total,
        "new_leads": new,
        "response_rate": 0  # 可擴展
    }

# ============ 啟動 ============

if __name__ == "__main__":
    print("🚀 啟動汽車保險潛客系統...")
    print("📁 資料庫:", db.db_path)
    print("🌐 網址: http://localhost:8000")
    print("📋 表單: http://localhost:8000/")
    print("⚙️ 管理後台: http://localhost:8000/admin")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")