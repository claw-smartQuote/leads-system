#!/bin/bash
# 港車北上報價系統 - 安卓APK打包腳本
# 需要在Linux環境（推薦Ubuntu 20.04+）下運行

set -e

echo "=========================================="
echo "港車北上報價系統 - APK打包工具"
echo "=========================================="
echo ""

# 檢查是否安裝了必要的工具
check_requirements() {
    echo "檢查環境..."
    
    # 檢查Python
    if ! command -v python3 &> /dev/null; then
        echo "錯誤：未安裝 Python3"
        exit 1
    fi
    
    # 檢查pip
    if ! command -v pip3 &> /dev/null; then
        echo "錯誤：未安裝 pip3"
        exit 1
    fi
    
    echo "✓ 環境檢查通過"
    echo ""
}

# 安裝依賴
install_deps() {
    echo "安裝依賴項..."
    
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
    pip3 install buildozer cython
    
    echo "✓ 依賴安裝完成"
    echo ""
}

# 安裝系統依賴（Ubuntu/Debian）
install_system_deps() {
    echo "安裝系統依賴（需要sudo權限）..."
    
    sudo apt update
    sudo apt install -y \
        git \
        zip \
        unzip \
        openjdk-17-jdk \
        python3-pip \
        autoconf \
        libtool \
        pkg-config \
        zlib1g-dev \
        libncurses5-dev \
        libncursesw5-dev \
        libtinfo5 \
        cmake \
        libffi-dev \
        libssl-dev \
        automake
    
    echo "✓ 系統依賴安裝完成"
    echo ""
}

# 初始化buildozer
init_buildozer() {
    echo "初始化Buildozer..."
    
    if [ ! -f "buildozer.spec" ]; then
        buildozer init
        echo "請編輯 buildozer.spec 配置文件後再次運行"
        exit 0
    fi
    
    echo "✓ Buildozer已初始化"
    echo ""
}

# 打包APK
build_apk() {
    echo "開始打包APK..."
    echo "這個過程可能需要20-60分鐘，請耐心等待..."
    echo ""
    
    # 清理舊構建
    buildozer android clean
    
    # 調試構建
    buildozer -v android debug
    
    echo ""
    echo "✓ APK打包完成！"
    echo ""
}

# 顯示幫助
show_help() {
    echo "使用方法："
    echo "  ./build_apk.sh          - 完整打包流程"
    echo "  ./build_apk.sh deps     - 僅安裝依賴"
    echo "  ./build_apk.sh build    - 僅執行打包"
    echo ""
    echo "輸出的APK文件位置："
    echo "  ./bin/gangchequote-1.5-arm64-v8a_armeabi-v7a-debug.apk"
    echo ""
}

# 主程序
main() {
    case "${1:-all}" in
        deps)
            check_requirements
            install_system_deps
            install_deps
            ;;
        build)
            build_apk
            ;;
        all|*)
            check_requirements
            install_deps
            init_buildozer
            build_apk
            
            echo "=========================================="
            echo "打包完成！"
            echo "=========================================="
            echo ""
            echo "APK文件位置："
            ls -lh bin/*.apk 2>/dev/null || echo "請檢查 bin/ 目錄"
            echo ""
            echo "安裝到安卓設備："
            echo "  buildozer android deploy run"
            echo ""
            ;;
    esac
}

# 運行主程序
main "$@"
