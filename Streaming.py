import numpy as np
import os
import h5py
# 假設您已將所有核心邏輯封裝在 radar_tracker_module.py 中
from RadarTracker_module import RadarProcessor 

# ===============================================
# 初始化區塊 (只需在程式啟動時執行一次)
# ===============================================

# 假設這些路徑是您在初始化時設定好的
BG_PATH = r"D:\visionware\pinre_home\no-people\_0001_2025_12_03_17_57_53.h5"
CALIBRATION_FOLDER = r"D:\visionware\pinre_home\no-people"

# 1. 初始化處理器（只需在整個系統啟動時執行一次）
# 這裡會自動完成載入背景和校準
radar_processor = RadarProcessor(
    bg_path=BG_PATH,
    calibration_folder_path=CALIBRATION_FOLDER,
    window_size=8
)


# ===============================================
# 核心 H5 串流處理函式
# ===============================================

def handle_incoming_h5_file(h5_file_path: str) -> list[dict]:
    """
    接收一個 H5 檔案路徑，模擬逐幀處理，並返回所有幀的狀態列表。

    h5_file_path: H5 檔案的路徑。
    
    Returns:
        list[dict]: 包含每一幀狀態 {"distance_safe": bool, "sitting": bool} 的列表。
    """
    print(f"\n[INFO] 開始處理傳入的 H5 檔案: {h5_file_path}")
    
    # 在處理新的 H5 檔案之前，重置內部狀態（歷史緩衝和單檔統計）
    # 這是必要的，因為 H5 檔案之間應該是獨立的測試
    radar_processor.tracker.history.clear()
    radar_processor.tracker.reset_single_file_stats()

    frame_results = []
    
    try:
        with h5py.File(h5_file_path, "r") as f:
            # 假設 RDI 數據位於 "DS1"[0]，形狀為 (32, 128, N)
            if "DS1" not in f:
                print("[ERROR] H5 檔案中找不到 'DS1' 資料集。")
                return []
                
            RDI = f["DS1"][0]
            num_frames = RDI.shape[2]
            
            print(f"[INFO] 檔案包含 {num_frames} 幀數據。")
            
            for i in range(num_frames):
                frame = RDI[:, :, i]  # 提取單一幀數據 (32, 128)
                
                # 2. 呼叫 get_state 處理即時幀
                state_result = radar_processor.get_state(frame)
                
                if state_result is not None:
                    # 3. 將結果儲存或傳遞給下一個模組
                    # state_result 格式為 {"distance_safe": True/False, "sitting": True/False}
                    frame_results.append(state_result)
                    
                    # 這裡可以加入將 state_result 即時傳輸到下一個警示模組的邏輯
                    # print(f"  Frame {i}: {state_result}") 
                    
        print(f"[INFO] 檔案處理完成。共輸出 {len(frame_results)} 個狀態。")
        
    except FileNotFoundError:
        print(f"[ERROR] H5 檔案不存在於路徑: {h5_file_path}")
    except Exception as e:
        print(f"[ERROR] 讀取或處理 H5 檔案時發生錯誤: {e}")
        
    return frame_results


# ===============================================
# 模擬調用 (取代您原來的 main 執行邏輯)
# ===============================================

if __name__ == "__main__":
    
    # 這裡放您的測試資料夾，模擬 H5 檔案是從這裡傳輸過來的
    test_folder = r"D:\visionware\pinre_home\test_first50_5000_correct"
    
    files = [f for f in os.listdir(test_folder) if f.endswith(".h5")]
    files.sort()

    if not files:
        print("[ERROR] 測試資料夾中找不到 H5 檔案。")
    
    # 模擬接收一個 H5 檔案路徑
    for fname in files:
        h5_file_path = os.path.join(test_folder, fname)
        
        # 呼叫 H5 處理函式，獲取該檔案中所有幀的狀態
        results_list = handle_incoming_h5_file(h5_file_path)
        
        if results_list:
            print(f"檔案 {fname} 的首 3 幀狀態: {results_list[:3]}")
        
    # 如果需要，也可以在這裡輸出累積的統計數據
    # print("\n累積總統計:", radar_processor.get_statistics())
