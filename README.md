# SmartQuote 潛客系統 - 部署配置文檔

## ⚠️ 重要配置規則

### Render Dashboard vs render.yaml 優先級

**問題**：Render Dashboard 的 Start Command 設置會 override `render.yaml` 配置！

**解決方案**：
1. 將 Start Command 設置為 `uvicorn app_v2:app --host 0.0.0.0 --port $PORT`
2. 或者刪除 Dashboard 覆蓋，只用 render.yaml

### 正確的 Start Command
```
uvicorn app_v2:app --host 0.0.0.0 --port $PORT
```

### 禁止使用的文件名
- ❌ `app.py` - 與舊版本衝突
- ❌ `app_simple.py` - 已廢棄
- ✅ `app_v2.py` - 當前版本

## 當前配置

### render.yaml
```yaml
services:
  - type: web
    name: leads-system
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app_v2:app --host 0.0.0.0 --port 10000
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
    plan: free
    autoDeploy: true
```

### Procfile (備用)
```
web: uvicorn app_v2:app --host 0.0.0.0 --port $PORT
```

### requirements.txt
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
jinja2==3.1.2
pandas==2.1.3
openpyxl==3.1.2
pydantic==2.5.0
requests==2.31.0
```

## 路由結構

| 路徑 | 功能 |
|-----|------|
| `/` | 前台表單 |
| `/admin` | 管理後台 |
| `/api/lead` | POST 提交潛客 |
| `/api/leads` | GET 所有潛客 |
| `/health` | 健康檢查 |

## 常見錯誤

### 1. RuntimeError: Directory 'static' does not exist
**原因**：使用舊版 app.py，引用了不存在的 static 目錄
**解決**：使用 app_v2.py，唔使用 static

### 2. Exited with status 1 - app.py not found
**原因**：Procfile 或 render.yaml 指向舊版 app.py
**解決**：確保所有配置指向 app_v2:app

### 3. 404 Not Found on /admin
**原因**：Render Dashboard Start Command override 緊舊配置
**解決**：手動更新 Dashboard Start Command 為 `uvicorn app_v2:app ...`

## 部署步驟

1. 本地修改代碼
2. `git add -A && git commit -m "message" && git push origin main`
3. Render 自動部署 或 手動 Deploy
4. 如果失敗，檢查 Dashboard Settings → Start Command

## 聯繫

- 前台：https://leads-system.onrender.com/
- 後台：https://leads-system.onrender.com/admin
- GitHub：git@github.com:claw-smartQuote/leads-system.git
