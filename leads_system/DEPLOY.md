# 🚀 一鍵部署到 Render

## 快速部署

### 步驟 1: 推送到 GitHub

你需要先把這個代碼推送到你的 GitHub 賬號：

```bash
# 1. 創建 GitHub 倉庫
# 訪問 https://github.com/new
# 倉庫名: leads-system
# 公開/私有都可以

# 2. 推送代碼（在 leads_system 目錄執行）
git remote add origin https://github.com/YOUR_USERNAME/leads-system.git
git branch -M main
git push -u origin main
```

---

### 步驟 2: 一鍵部署

把下面的鏈接中的 `YOUR_USERNAME` 替換成你的 GitHub 用戶名，然後點擊：

```
https://render.com/deploy?repo=https://github.com/YOUR_USERNAME/leads-system
```

或者手動部署：

1. 登入 [render.com](https://render.com)
2. 點擊 "New +" → "Web Service"
3. 選擇 "Build and deploy from a Git repository"
4. 連接你的 GitHub 並選擇 `leads-system` 倉庫
5. 配置如下：
   - **Name**: `leads-system`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
6. 點擊 "Create Web Service"

---

## 📋 部署後

部署完成後，你會獲得一個永久網址：
```
https://leads-system-xxx.onrender.com
```

**功能頁面：**
- 📝 客戶表單: `https://your-url.onrender.com/`
- ⚙️ 管理後台: `https://your-url.onrender.com/admin`
- 📊 API 文檔: `https://your-url.onrender.com/docs`
- 📥 Excel 匯出: `https://your-url.onrender.com/api/export`

---

## 🔧 環境變數（可選）

在 Render Dashboard → 你的服務 → Environment 可設置：

| 變數 | 說明 | 預設 |
|------|------|------|
| `WHATSAPP_TO` | WhatsApp 通知接收號碼 | +85221101144 |

---

## ⚠️ 注意事項

- **免費方案**：服務會在 15 分鐘無訪問後休眠，下次訪問需等待 30 秒喚醒
- **數據庫**：使用 SQLite，數據存儲在 Render 磁盤（免費方案每次部署會重置，建議考慮升級或定期備份）
- **自定義域名**：可在 Render 設置中添加自己的域名

---

## 🆘 故障排除

**部署失敗？**
1. 檢查 `requirements.txt` 是否正確
2. 檢查 `Procfile` 格式（注意大寫 P）
3. 查看 Render 日誌找錯誤

**服務無法啟動？**
1. 確認端口使用 `$PORT` 環境變數
2. 檢查 `app.py` 是否存在並正確

---

*最後更新: 2025-01*