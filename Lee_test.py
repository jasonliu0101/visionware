import os
import h5py
import numpy as np
from collections import deque


# ===============================================
# Step 0. 載入 nopeople 當背景（只做一次）
# ===============================================
def load_background(nopeople_path):
    print("[INFO] Loading background from nopeople...")
    with h5py.File(nopeople_path, "r") as f:
        RDI_no = f["DS1"][0]              # shape (32,128,N)
        bg = np.mean(RDI_no, axis=2)      # (32,128)
    print("[INFO] Background loaded.")
    return bg



# ===============================================
# Step 1. 計算一幀 RDI 的 residual_profile
# ===============================================
def compute_residual_profile(frame, bg):
    residual = frame - bg
    residual[residual < 0] = 0
    range_profile = np.max(residual, axis=1)  # (32,)
    return range_profile



# ===============================================
# Real-time classifier（新版：多幀平滑 + 變動量 + 動態校準）
# ===============================================
class RadarStateTracker:
    def __init__(self, bg, window_size=8):
        self.bg = bg
        self.history = deque(maxlen=window_size)  # 儲存最近 N 幀 avg residual
        self.window_size = window_size

        # ===== Sitting 判定閾值（修改為動態校準） =====
        self.STD_THRESHOLD = 0.0003            # 變動量閾值 (微動)
        self.AVG_THRESHOLD_FOR_SITTING = None  # 初始化為 None，等待校準！
        self.calibration_data = []             # 用於儲存無人數據的緩衝

        # ===== 統計計數（新增） =====
        self.count_distance_safe_true = 0
        self.count_distance_safe_false = 0
        self.count_sitting_true = 0
        self.count_sitting_false = 0

        # ===== 連續次數統計（新增） =====
        self.consecutive_true = 0
        self.consecutive_false = 0

        # 是否曾經達到 285 次（新增）
        self.has_true_285 = False
        self.has_false_285 = False

        # ===== 285 次事件計數 =====
        self.count_true_285_events = 0
        self.count_false_285_events = 0

        # 事件鎖（防止重複計數）
        self.true_event_lock = False
        self.false_event_lock = False


    def reset_single_file_stats(self):
        """
        重置單一檔案的統計計數和連續狀態，但保留整個 folder 的事件計數。
        """
        # 1. 重置單檔計數
        self.count_distance_safe_true  = 0
        self.count_distance_safe_false = 0
        self.count_sitting_true        = 0
        self.count_sitting_false       = 0

        # 2. 重置連續狀態
        self.consecutive_true = 0
        self.consecutive_false = 0
        self.true_event_lock = False
        self.false_event_lock = False


    def calibrate_avg_threshold(self, k=3):
        """
        使用收集到的 calibration_data (無人數據的 window_avg) 
        來設定 self.AVG_THRESHOLD_FOR_SITTING (mu + k*sigma)。
        """
        if not self.calibration_data:
            print("[WARNING] Calibration data is empty. Using default AVG threshold: 0.005")
            self.AVG_THRESHOLD_FOR_SITTING = 0.005
            return

        data = np.array(self.calibration_data)
        mu = np.mean(data)
        sigma = np.std(data)
        
        # 設定閾值 = 平均值 + k * 標準差
        new_threshold = mu + k * sigma
        
        # 確保閾值不會過低（設定最低安全值 0.001）
        self.AVG_THRESHOLD_FOR_SITTING = max(new_threshold, 0.001) 
        
        print(f"[INFO] Calibration done. Mu={mu:.6f}, Sigma={sigma:.6f}")
        print(f"[INFO] Set AVG_THRESHOLD_FOR_SITTING = {self.AVG_THRESHOLD_FOR_SITTING:.6f} (k={k})")
        
        # 清空校準數據
        self.calibration_data.clear()


    def process_frame(self, frame, is_calibrating=False):

        # Step 1: 計算 residual profile
        rp = compute_residual_profile(frame, self.bg)
        avg_val = float(np.mean(rp))

        # Step 2: 更新多幀緩衝
        self.history.append(avg_val)

        # 若尚未累積滿 window_size，先不判斷
        if len(self.history) < self.window_size:
            # 如果是校準模式，累積不滿時不做任何事
            if is_calibrating:
                return None 
            # 否則回傳預設值
            return {
                "distance_safe": True,
                "sitting": True,
                "avg_residual": avg_val,
                "window_avg": None,
                "window_std": None
            }

        # Step 3: 多幀統計
        window_avg = np.mean(self.history)
        window_std = np.std(self.history)
        
        # 【校準模式】：只儲存數據，不進行分類判斷
        if is_calibrating:
            self.calibration_data.append(window_avg)
            return None 

        # 確保已校準
        avg_thresh = self.AVG_THRESHOLD_FOR_SITTING if self.AVG_THRESHOLD_FOR_SITTING is not None else 0.005

        # ============================================
        # Sitting（是否有人）- 兩階段邏輯
        # ============================================
        sitting = False # 預設為無人
        
        # 階段 1: 檢查殘差平均值（物體大小/強度），太低判定為背景/雜訊
        if window_avg > avg_thresh: # 使用校準過的值
            # 階段 2: 檢查變動量（是否有微動），有微動才判定為有人
            if window_std > self.STD_THRESHOLD:
                sitting = True
        
        # ============================================
        # Distance Safe（是否 >= 40cm）
        # <40cm 時 residual 明顯偏高 (> 0.06)
        # ============================================
        if window_avg > 0.06:
            distance_safe = False
        else:
            distance_safe = True

        # ===== 統計更新 =====
        if distance_safe:
            self.count_distance_safe_true += 1
        else:
            self.count_distance_safe_false += 1

        # ===== 連續出現次數統計（新增） =====
        if distance_safe:
            self.consecutive_true += 1
            self.consecutive_false = 0
        else:
            self.consecutive_false += 1
            self.consecutive_true = 0

        # ===== 是否達到 285 次 =====

        # ---- True 連續事件 ----
        if self.consecutive_true >= 285:
            self.has_true_285 = True
            if not self.true_event_lock:
                self.count_true_285_events += 1
                self.true_event_lock = True
        else:
            self.true_event_lock = False


        # ---- False 連續事件 ----
        if self.consecutive_false >= 285:
            self.has_false_285 = True
            if not self.false_event_lock:
                self.count_false_285_events += 1
                self.false_event_lock = True
        else:
            self.false_event_lock = False


        if sitting:
            self.count_sitting_true += 1
        else:
            self.count_sitting_false += 1

        return {
            "distance_safe": distance_safe,
            "sitting": sitting,
            "avg_residual": avg_val,
            "window_avg": float(window_avg),
            "window_std": float(window_std)
        }



# ===============================================
# Step 4. 模擬 real-time（逐幀）
# ===============================================
def run_realtime_test_folder(folder_path, tracker):
    # 找出所有 .h5 檔案
    files = [f for f in os.listdir(folder_path) if f.endswith(".h5")]
    files.sort()

    if not files:
        print("[ERROR] No .h5 files found in folder:", folder_path)
        return

    print(f"[INFO] Found {len(files)} files in folder {folder_path}")

    # ===== 全資料夾的統計 =====
    total_distance_safe_true = 0
    total_distance_safe_false = 0
    total_sitting_true = 0
    total_sitting_false = 0

    # 逐檔處理
    for fname in files:
        fpath = os.path.join(folder_path, fname)
        print(f"\n============================================")
        print(f"[INFO] Processing file: {fname}")
        print(f"============================================")

        with h5py.File(fpath, "r") as f:
            RDI = f["DS1"][0]   # shape: (32,128,N)

        # 1. 清空 tracker 的歷史紀錄
        tracker.history.clear()
        
        # 2. 清空 tracker 的單檔計數和連續狀態
        tracker.reset_single_file_stats()

        # 逐幀
        for i in range(RDI.shape[2]):
            frame = RDI[:, :, i]
            # 運行正常模式（is_calibrating=False by default）
            result = tracker.process_frame(frame)

        # 累計檔案統計到「整個資料夾」的統計
        total_distance_safe_true  += tracker.count_distance_safe_true
        total_distance_safe_false += tracker.count_distance_safe_false
        total_sitting_true        += tracker.count_sitting_true
        total_sitting_false       += tracker.count_sitting_false

    # ====== 整個資料夾的總統計 ======
    print("\n============== TOTAL SUMMARY FOR FOLDER ==============")
    print(f"Total distance_safe = True  次數：{total_distance_safe_true}")
    print(f"Total distance_safe = False 次數：{total_distance_safe_false}")
    print(f"Total sitting       = True  次數：{total_sitting_true}")
    print(f"Total sitting       = False 次數：{total_sitting_false}")
    print("=======================================================\n")

    print("============== CONTINUOUS 285+ CHECK ================")
    print(f"是否曾連續 distance_safe=True  ≥285 次？ {tracker.has_true_285}")
    print(f"是否曾連續 distance_safe=False ≥285 次？ {tracker.has_false_285}")
    print("=======================================================\n")

    print(f"連續 True ≥285 次的事件數： {tracker.count_true_285_events}")
    print(f"連續 False ≥285 次的事件數： {tracker.count_false_285_events}")
    
    
# ===============================================
# Step 5. 新增：校準函式
# ===============================================
def run_calibration(nopeople_folder_path, tracker):
    print("\n[INFO] Starting AVG threshold calibration...")
    
    # 找出所有 .h5 檔案 (建議使用整個資料夾，但為了效率，只取第一個檔案)
    files = [f for f in os.listdir(nopeople_folder_path) if f.endswith(".h5")]
    files.sort()
    
    if not files:
        print("[ERROR] No .h5 files found for calibration in:", nopeople_folder_path)
        tracker.calibrate_avg_threshold(k=3) # 即使沒資料也要跑一次，使用預設值
        return

    # 這裡我們只使用第一個檔案進行校準，如果您希望使用多個檔案，請修改此處的迴圈
    fpath = os.path.join(nopeople_folder_path, files[0])
    print(f"[INFO] Using file: {files[0]} for calibration.")

    with h5py.File(fpath, "r") as f:
        RDI = f["DS1"][0]   # shape: (32,128,N)

    # 清空 history
    tracker.history.clear()
    
    # 逐幀處理 (is_calibrating=True)
    for i in range(RDI.shape[2]):
        frame = RDI[:, :, i]
        # 啟用校準模式
        tracker.process_frame(frame, is_calibrating=True) 

    # 執行校準計算 (使用 k=3)
    tracker.calibrate_avg_threshold(k=3)
    
    print("[INFO] Calibration finished.")



# ===============================================
# MAIN：執行流程
# ===============================================
if __name__ == "__main__":

    # 背景檔案路徑 (用於計算基礎背景)
    path_nopeople = r"D:\visionware\pinre_home\no-people\_0001_2025_12_03_17_57_53.h5"
    
    # 【新增】無人資料夾路徑 (用於動態校準 AVG 閾值)
    path_nopeople_folder = r"D:\visionware\pinre_home\no-people"
    
    # 測試資料夾路徑
    folder_test   = r"D:\visionware\pinre_home\test_first50_5000_error"
    #folder_test   = r"C:\Users\clara\Downloads\60cm_hclab\60cm_hclab"
    #folder_test   = r"C:\Users\clara\Downloads\no-people_hclab\no-people_hclab"

    # Step 0: 載入背景
    bg = load_background(path_nopeople)
    tracker = RadarStateTracker(bg, window_size=8)
    
    # Step 5: 【新增】校準階段
    run_calibration(path_nopeople_folder, tracker)

    # Step 4: 運行測試
    run_realtime_test_folder(folder_test, tracker)