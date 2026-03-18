# 潛客系統 - 一鍵部署

## 🚀 Deploy to Render

點擊下方按鈕一鍵部署：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/smartquote/leads-system)

---

## 📋 手動部署步驟

### 1. 複製代碼到 GitHub

```bash
cd leads_system
git init
git add .
git commit -m "Initial commit"
# 在 GitHub 創建倉庫，然後 push
git remote add origin https://github.com/YOUR_USERNAME/leads-system.git
git push -u origin main
```

### 2. 在 Render 部署

1. 登入 [render.com](https://render.com)
2. 點擊 "New +" → "Web Service"
3. 選擇你的 GitHub 倉庫
4. 配置：
   - **Name**: `leads-system`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. 點擊 "Create Web Service"

---

## 🔧 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `WHATSAPP_TO` | WhatsApp 通知接收號碼 | +85221101144 |
| `PORT` | 服務端口 | 10000 |

---

## 📁 文件說明

- `app.py` - FastAPI 主程式
- `database.py` - SQLite 資料庫
- `whatsapp_notifier.py` - WhatsApp 通知模組
- `export_excel.py` - Excel 匯出功能
- `templates/` - HTML 模板
- `static/` - 靜態文件

---

## 📝 功能

- ✅ 潛客資料收集表單
- ✅ 資料庫儲存
- ✅ WhatsApp 即時通知
- ✅ Excel 匯出
- ✅ 管理後台

---

*創建時間: 2025-01*