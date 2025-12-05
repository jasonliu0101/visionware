#!/bin/bash

# VisionWave Guardian 啟動腳本
# 用於啟動本地伺服器以支援瀏覽器通知功能

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

# 開啟瀏覽器
# 等待 1 秒確保伺服器已啟動
(sleep 1 && open "http://localhost:$PORT/index.html") &
(sleep 1 && open "http://localhost:$PORT/controller.html") &

# 啟動 Python HTTP 伺服器
echo "✅ 伺服器已啟動！請在瀏覽器中查看。"
echo "📝 按 Ctrl+C 停止伺服器"
cd "$DIR"
python3 -m http.server $PORT
