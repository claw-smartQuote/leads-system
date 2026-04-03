# 港車北上報價系統 - 部署指南

## 方案一：打包成安卓APK（推薦）

### 需要的環境
- Linux系統（推薦Ubuntu 20.04或更高版本）
- 或Windows下的WSL2（Windows Subsystem for Linux）
- 約10GB硬盤空間
- 穩定的網絡連接

### 部署步驟

#### 1. 在Linux環境下準備

```bash
# 安裝系統依賴（Ubuntu/Debian）
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip
sudo apt install -y autoconf libtool pkg-config zlib1g-dev
sudo apt install -y libncurses5-dev libncursesw5-dev libtinfo5
sudo apt install -y cmake libffi-dev libssl-dev automake
```

#### 2. 安裝Python依賴

```bash
cd ~/.openclaw/workspace/skills/insurance-quotation/android_app

# 安裝Python包
pip3 install kivy kivymd buildozer cython
```

#### 3. 打包APK

```bash
# 給腳本執行權限
chmod +x build_apk.sh

# 運行打包腳本
./build_apk.sh
```

或者手動打包：

```bash
# 初始化buildozer（首次運行）
buildozer init

# 編輯 buildozer.spec 配置文件

# 開始打包（調試版本）
buildozer -v android debug
```

#### 4. 獲取APK文件

打包完成後，APK文件將位於：
```
./bin/gangchequote-1.5-arm64-v8a_armeabi-v7a-debug.apk
```

#### 5. 安裝到安卓設備

```bash
# 自動部署並運行
buildozer android deploy run

# 或手動安裝
adb install bin/gangchequote-1.5-*.apk
```

---

## 方案二：Windows桌面版（測試用）

如果不能打包安卓APK，可以先在Windows上運行測試版本。

### 安裝步驟

1. 安裝Python 3.8+
   ```
   https://www.python.org/downloads/
   ```

2. 安裝依賴
   ```cmd
   pip install kivy kivymd
   ```

3. 運行應用
   ```cmd
   cd android_app
   python main.py
   ```

---

## 方案三：使用Docker打包（最簡單）

如果沒有Linux環境，可以使用Docker。

### 步驟

1. 安裝Docker
   ```
   https://www.docker.com/products/docker-desktop
   ```

2. 運行打包容器
   ```bash
   docker run -it --rm \
     -v $(pwd):/home/user/app \
     -w /home/user/app \
     kivy/buildozer:latest
   ```

3. 在容器內執行
   ```bash
   buildozer -v android debug
   ```

---

## 常見問題

### Q1: 打包過程中出現內存不足？
**A**: 建議至少有8GB RAM，並關閉其他程序。

### Q2: 如何修改應用圖標？
**A**: 準備一個512x512的PNG圖片，放入 `assets/logo.png`，然後在 `buildozer.spec` 中取消註釋：
```
android.icon = assets/logo.png
```

### Q3: 如何更新應用版本？
**A**: 修改 `buildozer.spec` 中的 `version` 數值。

### Q4: 打包失敗如何調試？
**A**: 查看日誌文件：
```bash
buildozer android logcat
```

---

## 聯系支持

如有問題，請聯系開發人員協助打包。
