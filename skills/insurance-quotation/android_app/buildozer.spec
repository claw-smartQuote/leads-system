[app]

# 應用名稱
title = 港車北上報價系統

# 包名（反向域名格式）
package.name = gangchequote
package.domain = com.smartquote

# 源代碼目錄
source.dir = .

# 主程序入口
source.main = main.py

# 包含的文件
source.include_exts = py,png,jpg,kv,atlas,ttf

# 版本
version = 1.5

# 依賴項
requirements = python3,kivy==2.2.1,kivymd==1.1.1

# 安卓API版本
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# 架構
android.archs = arm64-v8a, armeabi-v7a

# 權限
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 圖標
# android.icon = assets/logo.png

# 啟動畫面
# android.presplash = assets/presplash.png

# 屏幕方向
orientation = portrait

# 全屏
fullscreen = 0

[buildozer]

# 日誌級別
log_level = 2

# 警告模式
warn_on_root = 1
