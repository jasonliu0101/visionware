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
# Real-time classifier（新版：多幀平滑 + 變動量）
# ===============================================
class RadarStateTracker:
    def __init__(self, bg, window_size=8):
        self.bg = bg
        self.history = deque(maxlen=window_size)  # 儲存最近 N 幀 avg residual
        self.window_size = window_size

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




    def process_frame(self, frame):

        # Step 1: 計算 residual profile
        rp = compute_residual_profile(frame, self.bg)
        avg_val = float(np.mean(rp))

        # Step 2: 更新多幀緩衝
        self.history.append(avg_val)

        # 若尚未累積滿 window_size，先不判斷
        if len(self.history) < self.window_size:
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

        # ============================================
        # Sitting（是否有人）
        # 背景 std 幾乎=0；只要有微動 → std > 0.0003
        # ============================================
        if window_std < 0.0003:
            sitting = False
        else:
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
            if not self.true_event_lock:           # 第一次進入事件
                self.count_true_285_events += 1    # 計一次事件
                self.true_event_lock = True        # 上鎖避免重複計數
        else:
            self.true_event_lock = False           # 打斷後解鎖才能算下一次


        # ---- False 連續事件 ----
        if self.consecutive_false >= 285:
            self.has_false_285 = True
            if not self.false_event_lock:          # 第一次進入事件
                self.count_false_285_events += 1   # 計一次事件
                self.false_event_lock = True       # 上鎖
        else:
            self.false_event_lock = False          # 打斷後解鎖


    


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

        # 不清空 tracker 的總統計，只清空 history
        tracker.history.clear()

        # 逐幀
        for i in range(RDI.shape[2]):
            frame = RDI[:, :, i]
            result = tracker.process_frame(frame)

        # 累計檔案統計到「整個資料夾」的統計
        total_distance_safe_true  += tracker.count_distance_safe_true
        total_distance_safe_false += tracker.count_distance_safe_false
        total_sitting_true        += tracker.count_sitting_true
        total_sitting_false       += tracker.count_sitting_false

        # 處理完單一檔案後，清空 tracker 的單檔計數
        tracker.count_distance_safe_true  = 0
        tracker.count_distance_safe_false = 0
        tracker.count_sitting_true        = 0
        tracker.count_sitting_false       = 0

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
# MAIN：執行流程
# ===============================================
if __name__ == "__main__":

    path_nopeople = r"C:\Users\clara\Downloads\no-people_hclab\no-people_hclab\_0001_2025_12_04_17_25_59.h5"
    folder_test   = r"C:\Users\clara\Downloads\40cm_hclab\40cm_hclab"
    #folder_test   = r"C:\Users\clara\Downloads\60cm_hclab\60cm_hclab"
    #folder_test   = r"C:\Users\clara\Downloads\no-people_hclab\no-people_hclab"

    bg = load_background(path_nopeople)
    tracker = RadarStateTracker(bg, window_size=8)

    run_realtime_test_folder(folder_test, tracker)



