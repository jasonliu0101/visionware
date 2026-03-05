"""
VisionWave Guardian - API Server
Flask 伺服器，整合 RadarProcessor 後端與前端介面
"""

import os
import sys
import tempfile
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# 將上層目錄加入 path，以便匯入 RadarProcessor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from RadarTracker_module import RadarProcessor
    import h5py
    import numpy as np
    RADAR_AVAILABLE = True
except ImportError:
    RADAR_AVAILABLE = False
    print("⚠️  RadarProcessor 模組未載入（缺少依賴），系統以獨立前端模式啟動")

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ========================================
# 共享狀態（由雷達後端或 API 更新）
# ========================================
shared_state = {
    "distance_safe": True,
    "sitting": False
}
state_lock = threading.Lock()

# ========================================
# 雷達處理器初始化
# ========================================
radar_processor = None

def init_radar():
    """嘗試初始化 RadarProcessor（需要環境變數或預設路徑）"""
    global radar_processor

    if not RADAR_AVAILABLE:
        return

    bg_path = os.environ.get('RADAR_BG_PATH', '')
    cal_path = os.environ.get('RADAR_CAL_PATH', '')

    if not bg_path or not cal_path:
        print("ℹ️  未設定 RADAR_BG_PATH / RADAR_CAL_PATH 環境變數")
        print("   設定方式：")
        print("   export RADAR_BG_PATH=/path/to/nopeople.h5")
        print("   export RADAR_CAL_PATH=/path/to/nopeople_folder/")
        print("   系統將以 API 模式運行（透過 POST /api/status 手動更新狀態）")
        return

    try:
        radar_processor = RadarProcessor(
            bg_path=bg_path,
            calibration_folder_path=cal_path,
            window_size=8
        )
        print("✅ RadarProcessor 初始化完成")
    except Exception as e:
        print(f"❌ RadarProcessor 初始化失敗: {e}")


# ========================================
# 靜態頁面路由
# ========================================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


# ========================================
# API 端點
# ========================================
@app.route('/api/status', methods=['GET'])
def get_status():
    """取得目前感測狀態"""
    with state_lock:
        return jsonify(shared_state)


@app.route('/api/status', methods=['POST'])
def update_status():
    """
    手動更新狀態（供外部程式或整合使用）
    Body: {"distance_safe": bool, "sitting": bool}
    """
    data = request.get_json()
    if data:
        with state_lock:
            if 'distance_safe' in data:
                shared_state['distance_safe'] = bool(data['distance_safe'])
            if 'sitting' in data:
                shared_state['sitting'] = bool(data['sitting'])
    return jsonify(shared_state)


@app.route('/api/upload', methods=['POST'])
def upload_h5():
    """
    上傳 H5 檔案，使用 RadarProcessor 逐幀處理並更新狀態。
    最後一幀的結果會成為目前的系統狀態。
    """
    if not RADAR_AVAILABLE or radar_processor is None:
        return jsonify({"error": "RadarProcessor 未初始化，請設定環境變數後重啟"}), 503

    if 'file' not in request.files:
        return jsonify({"error": "請提供 H5 檔案（form field: file）"}), 400

    file = request.files['file']
    if not file.filename.endswith('.h5'):
        return jsonify({"error": "僅支援 .h5 檔案格式"}), 400

    # 儲存暫存檔案並處理
    try:
        with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        results = []
        with h5py.File(tmp_path, 'r') as f:
            if 'DS1' not in f:
                return jsonify({"error": "H5 檔案中找不到 DS1 資料集"}), 400

            RDI = f['DS1'][0]
            num_frames = RDI.shape[2]

            # 重置追蹤器狀態
            radar_processor.tracker.history.clear()
            radar_processor.tracker.reset_single_file_stats()

            for i in range(num_frames):
                frame = RDI[:, :, i]
                state_result = radar_processor.get_state(frame)
                if state_result is not None:
                    results.append(state_result)

        # 以最後一幀結果更新共享狀態
        if results:
            with state_lock:
                shared_state['distance_safe'] = results[-1]['distance_safe']
                shared_state['sitting'] = results[-1]['sitting']

        os.unlink(tmp_path)

        return jsonify({
            "frames_processed": len(results),
            "current_state": shared_state,
            "statistics": radar_processor.get_statistics()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/info', methods=['GET'])
def system_info():
    """系統資訊端點"""
    return jsonify({
        "system": "VisionWave Guardian",
        "version": "1.0.0",
        "radar_available": RADAR_AVAILABLE,
        "radar_initialized": radar_processor is not None,
    })


# ========================================
# 啟動
# ========================================
if __name__ == '__main__':
    init_radar()

    print()
    print("🚀 VisionWave Guardian API Server")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📡 前端介面:  http://localhost:8000")
    print(f"📊 狀態 API:  http://localhost:8000/api/status")
    print(f"📁 上傳端點:  http://localhost:8000/api/upload")
    print(f"ℹ️  系統資訊:  http://localhost:8000/api/info")
    print(f"🔬 雷達模組:  {'✅ 已載入' if RADAR_AVAILABLE else '❌ 未載入'}")
    print(f"🎯 雷達處理器: {'✅ 已初始化' if radar_processor else '⏳ 等待設定'}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    app.run(host='0.0.0.0', port=8000, debug=True)
