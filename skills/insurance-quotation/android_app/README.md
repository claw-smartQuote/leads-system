# 港車北上報價系統 - Android App

使用 Kivy 框架開發的安卓應用，支持港車北上汽車保險報價。

## 功能特點

- 📱 原生安卓APP體驗
- 🔥 支持燃油車報價
- ⚡ 支持新能源車報價
- 🎂 自動根據車齡計算折扣
- 💾 本地計算，無需網絡
- 📋 報價單生成與分享

## 技術棧

- **框架**：Kivy / KivyMD
- **語言**：Python 3
- **打包工具**：Buildozer

## 文件結構

```
android_app/
├── main.py              # 應用入口
├── quotation_system.py  # 報價系統（復製自技能目錄）
├── screens/
│   ├── __init__.py
│   ├── home_screen.py   # 主頁面
│   ├── quote_screen.py  # 報價頁面
│   └── result_screen.py # 結果頁面
├── widgets/
│   ├── __init__.py
│   └── custom_widgets.py # 自定義組件
├── assets/
│   ├── logo.png         # 應用圖標
│   └── fonts/           # 字體文件
├── buildozer.spec       # 打包配置
└── requirements.txt     # 依賴列表
```

## 安裝與運行

### 1. 安裝依賴

```bash
pip install kivy kivymd
```

### 2. 運行測試

```bash
cd android_app
python main.py
```

### 3. 打包APK（需要Linux環境）

```bash
# 安裝buildozer
pip install buildozer

# 初始化配置
buildozer init

# 打包APK
buildozer -v android debug
```

## 使用說明

1. 打開APP後選擇車輛類型（燃油車/新能源車）
2. 輸入車牌號碼
3. 選擇使用性質（6座以下/6-10座）
4. 輸入乘客數量
5. 輸入車齡（年）
6. 選擇第三者責任險保額
7. 可選：添加車上人員險、駕意險
8. 點擊「計算報價」生成報價單
9. 可分享報價單至WhatsApp/微信

## 注意事項

- 首次打包需要在Linux環境下進行
- 需要安裝Android SDK和NDK
- 建議使用Ubuntu或Docker環境進行打包
