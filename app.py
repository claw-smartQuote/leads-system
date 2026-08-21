"""
FastAPI 主程式 - 汽車保險潛客系統
"""
import os
import sys
import json
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
    """管理後台（完整版 - 查看/刪除/標記）"""
    leads = db.get_all_leads()
    new_count = db.get_new_leads_count()
    
    leads_json = json.dumps(leads, ensure_ascii=False, default=str)
    
    rows = ""
    for lead in leads[:50]:
        status = lead.get('status', '新潛客')
        status_map = {'新潛客': 'status-new', '已聯絡': 'status-contacted', '已報價': 'status-quoted', '已成交': 'status-won'}
        sc = status_map.get(status, 'status-new')
        lid = lead.get('id', '')
        name = str(lead.get('name', '-')).replace('<', '&lt;').replace('>', '&gt;')
        phone = str(lead.get('phone', '-')).replace('<', '&lt;')
        car_plate = str(lead.get('car_plate') or '-').replace('<', '&lt;')
        car_model = str(lead.get('car_model') or '-').replace('<', '&lt;')
        expiry = str(lead.get('expiry_date') or '-')
        inquiry = str(lead.get('inquiry_type') or '-')
        rows += (
            '<tr>'
            '<td>#' + str(lid) + '</td>'
            '<td>' + name + '</td>'
            '<td>' + phone + '</td>'
            '<td>' + car_plate + '</td>'
            '<td>' + car_model + '</td>'
            '<td>' + expiry + '</td>'
            '<td>' + inquiry + '</td>'
            '<td><span class="status ' + sc + '">' + status + '</span></td>'
            '<td>'
            '<button class="btn btn-view" onclick="viewLead(' + str(lid) + ')">查看</button>'
            '<button class="btn btn-contact" onclick="updateStatus(' + str(lid) + ', \'已聯絡\')">已聯絡</button>'
            '<button class="btn btn-delete" onclick="deleteLead(' + str(lid) + ')">刪除</button>'
            '</td>'
            '</tr>\n'
        )
    
    if not rows:
        rows = '<tr><td colspan="9" style="text-align:center;color:#999;padding:40px;">暫無資料</td></tr>'
    
    html = '<!DOCTYPE html>\n<html>\n<head>\n'
    html += '<meta charset="utf-8">\n'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>潛客管理後台</title>\n'
    html += '<style>\n'
    html += 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }\n'
    html += '.container { max-width: 1400px; margin: 0 auto; }\n'
    html += 'h1 { color: #333; }\n'
    html += '.stats { display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }\n'
    html += '.stat-box { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; text-align: center; min-width: 140px; }\n'
    html += '.stat-box h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; }\n'
    html += '.stat-box .number { font-size: 32px; font-weight: bold; color: #667eea; }\n'
    html += '.table-wrap { overflow-x: auto; }\n'
    html += 'table { width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px; border-collapse: collapse; }\n'
    html += 'th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; white-space: nowrap; }\n'
    html += 'th { background: #667eea; color: white; font-weight: 500; }\n'
    html += 'tr:hover { background: #f9f9f9; }\n'
    html += '.btn { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-right: 4px; }\n'
    html += '.btn-view { background: #667eea; color: white; }\n'
    html += '.btn-delete { background: #dc3545; color: white; }\n'
    html += '.btn-contact { background: #4caf50; color: white; }\n'
    html += '.status { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }\n'
    html += '.status-new { background: #e3f2fd; color: #1976d2; }\n'
    html += '.status-contacted { background: #fff3e0; color: #f57c00; }\n'
    html += '.status-quoted { background: #f3e5f5; color: #7b1fa2; }\n'
    html += '.status-won { background: #e8f5e9; color: #388e3c; }\n'
    html += '.actions { margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap; }\n'
    html += '.btn-action { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }\n'
    html += '.btn-primary { background: #667eea; color: white; }\n'
    html += '.btn-export { background: #ff9800; color: white; }\n'
    html += '.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }\n'
    html += '.modal-content { background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 80px auto; max-height: 75vh; overflow-y: auto; }\n'
    html += '.modal h2 { margin-top: 0; color: #333; }\n'
    html += '.modal-close { float: right; cursor: pointer; font-size: 28px; color: #999; line-height: 1; }\n'
    html += '.modal-close:hover { color: #333; }\n'
    html += '.detail-table { width: 100%; border-collapse: collapse; }\n'
    html += '.detail-table td { padding: 10px 8px; border-bottom: 1px solid #eee; }\n'
    html += '.detail-table td:first-child { font-weight: 600; color: #667eea; width: 130px; white-space: nowrap; }\n'
    html += '</style>\n</head>\n<body>\n'
    html += '<div class="container">\n'
    html += '<h1>📋 潛客管理後台</h1>\n'
    html += '<div class="stats">\n'
    html += '<div class="stat-box"><h3>總潛客數</h3><div class="number">' + str(len(leads)) + '</div></div>\n'
    html += '<div class="stat-box"><h3>新潛客</h3><div class="number">' + str(new_count) + '</div></div>\n'
    html += '</div>\n'
    html += '<div class="actions">\n'
    html += '<a href="/" target="_blank" class="btn-action btn-primary">🌐 查看表單</a>\n'
    html += '<a href="/api/export" class="btn-action btn-export">📊 匯出 Excel</a>\n'
    html += '</div>\n'
    html += '<div class="table-wrap"><table>\n'
    html += '<thead><tr><th>編號</th><th>姓名</th><th>電話</th><th>車牌</th><th>車型</th><th>到期日</th><th>查詢類型</th><th>狀態</th><th>操作</th></tr></thead>\n'
    html += '<tbody>' + rows + '</tbody>\n'
    html += '</table></div>\n'
    html += '</div>\n'
    
    # Modal
    html += '<div id="leadModal" class="modal">\n'
    html += '<div class="modal-content">\n'
    html += '<span class="modal-close" onclick="closeModal()">&times;</span>\n'
    html += '<h2>📋 潛客詳細資料</h2>\n'
    html += '<div id="leadDetails"></div>\n'
    html += '</div></div>\n'
    
    # JavaScript
    html += '<script>\n'
    html += 'var leads = ' + leads_json + ';\n'
    html += """
function viewLead(id) {
    var lead = null;
    for (var i = 0; i < leads.length; i++) { if (leads[i].id == id) { lead = leads[i]; break; } }
    if (!lead) { alert('找不到記錄'); return; }
    var labels = {id:'編號',name:'姓名',phone:'電話',email:'電郵/微信',car_plate:'車牌',car_model:'車型',car_year:'車齡',current_insurer:'現有保險公司',expiry_date:'到期日',inquiry_type:'查詢類型',notes:'備註',status:'狀態',created_at:'提交時間',follow_up_date:'跟進日期'};
    var h = '<table class="detail-table">';
    for (var k in lead) { if (lead[k] && k !== 'password') { h += '<tr><td>' + (labels[k]||k) + ':</td><td>' + lead[k] + '</td></tr>'; } }
    h += '</table>';
    document.getElementById('leadDetails').innerHTML = h;
    document.getElementById('leadModal').style.display = 'block';
}

function deleteLead(id) {
    var name = '';
    for (var i = 0; i < leads.length; i++) { if (leads[i].id == id) { name = leads[i].name || ''; break; } }
    if (!confirm('確定要刪除「' + name + '」(ID:' + id + ') 嗎？')) return;
    fetch('/api/leads/' + id, { method: 'DELETE' })
        .then(function(r) { return r.json(); })
        .then(function(d) { if (d.success) { alert('已刪除'); location.reload(); } else { alert('失敗: ' + (d.detail||d.message||'')); } })
        .catch(function(e) { alert('錯誤: ' + e); });
}

async function updateStatus(id, status) {
    await fetch('/api/leads/' + id + '/status', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({status: status}) });
    location.reload();
}

function closeModal() { document.getElementById('leadModal').style.display = 'none'; }
window.onclick = function(e) { if (e.target == document.getElementById('leadModal')) closeModal(); };
"""
    html += '</script>\n</body>\n</html>'
    
    return HTMLResponse(content=html)

# ============ API 路由 ============

@app.post("/api/leads", response_model=dict)
async def create_lead(lead: LeadCreate):
    """創建新潛客"""
    try:
        lead_data = lead.dict()
        lead_id = db.add_lead(lead_data)
        try:
            notifier.send_new_lead_notification(lead_data, lead_id)
        except Exception as e:
            print(f"WhatsApp 通知發送失敗: {e}")
        return {"success": True, "message": "潛客資料已提交", "lead_id": lead_id}
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
    return {"total_leads": total, "new_leads": new, "response_rate": 0}

@app.get("/health")
async def health():
    return {"status": "ok"}

# ============ 啟動 ============

if __name__ == "__main__":
    print("🚀 啟動汽車保險潛客系統...")
    print("📁 資料庫:", db.db_path)
    print("🌐 網址: http://localhost:8000")
    print("📋 表單: http://localhost:8000/")
    print("⚙️ 管理後台: http://localhost:8000/admin")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
