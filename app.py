"""
FastAPI 主程式 - 汽車保險潛客系統
"""
import os
import sys
from datetime import datetime
from pathlib import Path
import json

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
    """管理後台（完整版）"""
    leads = db.get_all_leads()
    new_count = db.get_new_leads_count()
    
    # 準備 JSON 數據供 JavaScript 使用
    leads_json = json.dumps(leads, ensure_ascii=False, default=str)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>潛客管理後台</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            h1 {{ color: #333; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; text-align: center; }}
            .stat-box h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
            .stat-box .number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
            table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #667eea; color: white; font-weight: 500; }}
            tr:hover {{ background: #f9f9f9; }}
            .btn {{ padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-right: 5px; }}
            .btn-view {{ background: #667eea; color: white; }}
            .btn-delete {{ background: #dc3545; color: white; }}
            .btn-contact {{ background: #4caf50; color: white; }}
            .status {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
            .status-新潛客 {{ background: #e3f2fd; color: #1976d2; }}
            .status-已聯絡 {{ background: #fff3e0; color: #f57c00; }}
            .status-已報價 {{ background: #f3e5f5; color: #7b1fa2; }}
            .status-已成交 {{ background: #e8f5e9; color: #388e3c; }}
            .actions {{ margin: 20px 0; display: flex; gap: 10px; }}
            .btn-action {{ padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }}
            .btn-primary {{ background: #667eea; color: white; }}
            .btn-export {{ background: #ff9800; color: white; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }}
            .modal-content {{ background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 100px auto; max-height: 70vh; overflow-y: auto; }}
            .modal h2 {{ margin-top: 0; color: #333; }}
            .modal-close {{ float: right; cursor: pointer; font-size: 28px; color: #999; }}
            .modal-close:hover {{ color: #333; }}
            .detail-table {{ width: 100%; }}
            .detail-table td {{ padding: 8px; border-bottom: 1px solid #eee; }}
            .detail-table td:first-child {{ font-weight: 600; color: #667eea; width: 120px; }}
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
                <a href="/" target="_blank" class="btn-action btn-primary">🌐 查看表單</a>
                <a href="/api/export" class="btn-action btn-export">📊 匯出 Excel</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>編號</th>
                        <th>姓名</th>
                        <th>電話</th>
                        <th>車牌</th>
                        <th>車型</th>
                        <th>到期日</th>
                        <th>查詢類型</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for lead in leads[:50]:
        status_map = {{'新潛客': 'status-新潛客', '已聯絡': 'status-已聯絡', '已報價': 'status-已報價', '已成交': 'status-已成交'}}
        status_class = status_map.get(lead.get('status', '新潛客'), 'status-新潛客')
        
        html_content += f"""
                    <tr>
                        <td>#{{lead['id']}}</td>
                        <td>{{lead.get('name', '-')}}</td>
                        <td>{{lead.get('phone', '-')}}</td>
                        <td>{{lead.get('car_plate', '-')}}</td>
                        <td>{{lead.get('car_model', '-')}}</td>
                        <td>{{lead.get('expiry_date', '-')}}</td>
                        <td>{{lead.get('inquiry_type', '-')}}</td>
                        <td><span class="status {{status_class}}">{{lead.get('status', '新潛客')}}</span></td>
                        <td>
                            <button class="btn btn-view" onclick="viewLead({{lead['id']}})">查看</button>
                            <button class="btn btn-contact" onclick="updateStatus({{lead['id']}}, '已聯絡')">已聯絡</button>
                            <button class="btn btn-delete" onclick="deleteLead({{lead['id']}}, '{{lead.get('name', '')}}')">刪除</button>
                        </td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <!-- 查看詳情 Modal -->
        <div id="leadModal" class="modal">
            <div class="modal-content">
                <span class="modal-close" onclick="closeModal()">&times;</span>
                <h2>📋 潛客詳細資料</h2>
                <div id="leadDetails"></div>
            </div>
        </div>
        
        <script>
            let leads = """ + leads_json + """;
            
            function viewLead(id) {
                const lead = leads.find(function(l) { return l.id == id; });
                if (!lead) { alert('找不到記錄'); return; }
                
                const fieldNames = {
                    'id': '編號', 'name': '姓名', 'phone': '電話', 'email': '電郵',
                    'car_plate': '車牌', 'car_model': '車型', 'car_year': '車齡',
                    'current_insurer': '現有保險公司', 'expiry_date': '到期日',
                    'inquiry_type': '查詢類型', 'notes': '備註', 'status': '狀態',
                    'created_at': '提交時間', 'follow_up_date': '跟進日期'
                };
                
                let html = '<table class="detail-table">';
                for (let [key, value] of Object.entries(lead)) {
                    if (value && key !== 'password') {
                        let label = fieldNames[key] || key;
                        html += '<tr><td>' + label + ':</td><td>' + value + '</td></tr>';
                    }
                }
                html += '</table>';
                
                document.getElementById('leadDetails').innerHTML = html;
                document.getElementById('leadModal').style.display = 'block';
            }
            
            function deleteLead(id, name) {
                if (!confirm('確定要刪除「' + name + '」嗎？此操作無法撤銷！')) return;
                fetch('/api/leads/' + id, { method: 'DELETE' })
                    .then(function(response) { return response.json(); })
                    .then(function(data) {
                        if (data.success) {
                            alert('已刪除');
                            location.reload();
                        } else {
                            alert('刪除失敗: ' + (data.detail || data.message || '未知錯誤'));
                        }
                    })
                    .catch(function(e) {
                        alert('刪除失敗: ' + e);
                    });
            }
            
            async function updateStatus(id, status) {
                await fetch('/api/leads/' + id + '/status', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({status: status})
                });
                location.reload();
            }
            
            function closeModal() {
                document.getElementById('leadModal').style.display = 'none';
            }
            
            window.onclick = function(event) {
                if (event.target == document.getElementById('leadModal')) {
                    closeModal();
                }
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

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: int):
    """刪除指定潛客"""
    try:
        success = db.delete_lead(lead_id)
        if success:
            return {"success": True, "message": "已刪除"}
        else:
            raise HTTPException(status_code=404, detail="潛客不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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