# 部署指南 - 免費方案

## 🎯 目標
讓客戶可以從外部訪問你的潛客表單，完全免費！

## 📋 方案選擇

### 方案 A: ngrok（最簡單，適合測試）
將你的本地電腦變成臨時網站，客戶可以從任何地方訪問。

**優點：**
- 完全免費
- 5分鐘搭建
- 無需伺服器

**缺點：**
- 網址每次重啟會變（可用固定網址付費版）
- 電腦需要一直開著

### 方案 B: Render（推薦，適合長期）
免費雲端托管，24小時在線。

**優點：**
- 永久免費網址
- 24小時在線
- 自動 HTTPS

**缺點：**
- 免費版有休眠（15分鐘無訪問會休眠，首次訪問需 30 秒喚醒）

---

## 🚀 方案 A: ngrok 部署

### 步驟 1: 安裝 ngrok
```bash
# macOS
brew install ngrok

# 或手動安裝
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### 步驟 2: 註冊 ngrok 賬號
1. 訪問 https://ngrok.com
2. 免費註冊
3. 獲取 Authtoken

### 步驟 3: 配置 ngrok
```bash
ngrok config add-authtoken YOUR_TOKEN
```

### 步驟 4: 啟動系統
```bash
# 終端 1: 啟動後端
cd ~/.openclaw/workspace/leads_system
./start.sh

# 終端 2: 啟動 ngrok
ngrok http 8000
```

### 步驟 5: 獲取網址
ngrok 會顯示類似：
```
Forwarding: https://abc123.ngrok-free.app -> http://localhost:8000
```

把 `https://abc123.ngrok-free.app` 發給客戶即可！

---

## 🚀 方案 B: Render 部署（推薦長期）

### 步驟 1: 準備代碼
確保以下文件已創建：
- `render.yaml`（Render 配置文件）
- `requirements.txt`（已創建）
- `app.py`（已創建）

### 步驟 2: 上傳到 GitHub
```bash
# 在 leads_system 目錄
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/leads-system.git
git push -u origin main
```

### 步驟 3: Render 部署
1. 訪問 https://render.com
2. 用 GitHub 登錄
3. 點擊 "New Web Service"
4. 選擇你的 GitHub 倉庫
5. 配置：
   - **Name**: leads-system
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port 10000`
6. 點擊 "Create Web Service"

### 步驟 4: 獲取網址
Render 會自動分配一個永久網址，例如：
```
https://leads-system.onrender.com
```

---

## 📱 WhatsApp 通知配置

目前 WhatsApp 通知會生成觸發文件。要實現真正自動發送，有幾個選項：

### 選項 1: 使用 OpenClaw（推薦）
讓我幫你在收到新潛客時通過 OpenClaw 發送 WhatsApp。

### 選項 2: 使用第三方服務
- Twilio（付費，穩定）
- CallMeBot（免費，有限制）

---

## 🔒 安全建議

1. **資料備份**：定期備份 `data/leads.db` 和 `exports/` 目錄
2. **HTTPS**：ngrok 和 Render 都自動提供 HTTPS
3. **訪問控制**：管理後台 `/admin` 建議添加密碼保護

---

## 📝 下一步

1. ✅ 先在本地測試系統
2. ✅ 選擇部署方案（ngrok 或 Render）
3. ✅ 配置 WhatsApp 通知
4. ✅ 分享表單給客戶

需要我幫你完成哪一步？