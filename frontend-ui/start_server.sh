#!/bin/bash

# VisionWave Guardian 啟動腳本
# 啟動 Flask API 伺服器，整合前端介面與雷達後端

PORT=8000
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 正在啟動 VisionWave Guardian..."
echo "📂 服務目錄: $DIR"
echo "🌐 伺服器端口: $PORT"

# 檢查端口是否被佔用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ 端口 $PORT 已被佔用，嘗試使用 8001..."
    PORT=8001
fi

# 檢查 Flask 是否已安裝
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 安裝必要套件..."
    pip3 install flask flask-cors
fi

# 開啟瀏覽器（等待 2 秒確保伺服器已啟動）
(sleep 2 && open "http://localhost:$PORT") &

# 啟動 Flask API 伺服器
echo "✅ 伺服器啟動中..."
echo "📝 按 Ctrl+C 停止伺服器"
cd "$DIR"
python3 server.py
