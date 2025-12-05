import os
import csv
import h5py
import numpy as np
from collections import deque


# ===============================================
# Step 0. 載入 nopeople 當背景 + 根據 nopeople 計算 sitting 門檻
# ===============================================
def compute_residual_and_energy(frame, bg):
    """
    frame: 單一幀 RDI, shape = (32, 128)
    bg   : 背景平均,   shape = (32, 128)

    回傳:
      range_profile: 每個 range bin 的最大 residual (32,)
      energy       : 這一幀的 residual 總能量 (scalar)
    """
    residual = frame - bg
    residual[residual < 0] = 0
    range_profile = np.max(residual, axis=1)     # (32,)
    energy = float(np.sum(residual))             # scalar
    return range_profile, energy


def load_background(nopeople_path):
    print("[INFO] Loading background from nopeople...")
    with h5py.File(nopeople_path, "r") as f:
        RDI_no = f["DS1"][0]              # shape (32,128,N)
        bg = np.mean(RDI_no, axis=2)      # (32,128)

        # ==== 使用「同一種 residual 演算法」計算背景能量 ====
        bg_energies = []
        for i in range(RDI_no.shape[2]):
            _, e = compute_residual_and_energy(RDI_no[:, :, i], bg)
            bg_energies.append(e)

        bg_energies = np.array(bg_energies)
        mu = float(np.mean(bg_energies))
        sigma = float(np.std(bg_energies))

        # 門檻 = 背景平均 + 3 倍標準差
        # （3 可以再調整；越大越保守）
        sitting_threshold = mu + 3 * sigma

    print("[INFO] Background loaded.")
    print("[INFO] bg_energy mean =", mu)
    print("[INFO] bg_energy std  =", sigma)
    print("[INFO] Sitting threshold (dynamic) =", sitting_threshold)

    return bg, sitting_threshold


# ===============================================
# Real-time classifier
# ===============================================
class RadarStateTracker:
    def __init__(self, bg, sitting_threshold, window_size=8):
        self.bg = bg
        self.sitting_threshold = sitting_threshold
        self.history = deque(maxlen=window_size)  # 儲存最近 N 幀 avg residual
        self.window_size = window_size

        # ===== 統計計數 =====
        self.count_distance_safe_true = 0
        self.count_distance_safe_false = 0
        self.count_sitting_true = 0
        self.count_sitting_false = 0

        # ===== 連續次數統計 =====
        self.consecutive_true = 0
        self.consecutive_false = 0

        # 是否曾經達到 285 次
        self.has_true_285 = False
        self.has_false_285 = False

        # 285 次事件計數
        self.count_true_285_events = 0
        self.count_false_285_events = 0

        # 事件鎖（防止重複計數）
        self.true_event_lock = False
        self.false_event_lock = False


    def process_frame(self, frame):

        # Step 1: residual profile + energy（唯一標準）
        rp, energy = compute_residual_and_energy(frame, self.bg)
        avg_val = float(np.mean(rp))  # 還保留給 distance 判斷用

        # Step 2: 更新多幀緩衝（給 distance_safe 判斷）
        self.history.append(avg_val)

        # 若尚未累積滿 window_size，先不判斷（回傳預設 true/true）
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

        # ==============================
        # Sitting（是否有人）
        # 用「residual 總能量」 vs 動態門檻
        # ==============================
        if energy > self.sitting_threshold:
            sitting = True
        else:
            sitting = False

        # ==============================
        # Distance Safe（是否 >= 40cm）
        # 這邊沿用你原本的 window_avg 規則
        # ==============================
        if window_avg > 0.06:
            distance_safe = False   # 太近
        else:
            distance_safe = True    # 安全

        # ===== 統計更新 =====
        if distance_safe:
            self.count_distance_safe_true += 1
        else:
            self.count_distance_safe_false += 1

        if sitting:
            self.count_sitting_true += 1
        else:
            self.count_sitting_false += 1

        # ===== 連續出現次數統計 =====
        if distance_safe:
            self.consecutive_true += 1
            self.consecutive_false = 0
        else:
            self.consecutive_false += 1
            self.consecutive_true = 0

        # ===== 是否達到 285 次（含事件計數） =====
        if self.consecutive_true >= 285:
            self.has_true_285 = True
            if not self.true_event_lock:
                self.count_true_285_events += 1
                self.true_event_lock = True
        else:
            self.true_event_lock = False

        if self.consecutive_false >= 285:
            self.has_false_285 = True
            if not self.false_event_lock:
                self.count_false_285_events += 1
                self.false_event_lock = True
        else:
            self.false_event_lock = False

        return {
            "distance_safe": distance_safe,
            "sitting": sitting,
            "avg_residual": avg_val,
            "window_avg": float(window_avg),
            "window_std": float(window_std)
        }


# ===============================================
# Step 4. 模擬 real-time（逐幀）+ 輸出 CSV
# ===============================================
def run_realtime_test_folder(folder_path, tracker):

    all_frame_results = []   # 紀錄所有偵

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
        print(f"[INFO] Processing file: {fname}")

        with h5py.File(fpath, "r") as f:
            RDI = f["DS1"][0]   # shape: (32,128,N)

        # 不清空 tracker 的總統計，只清空 history
        tracker.history.clear()

        # 逐幀
        for i in range(RDI.shape[2]):
            frame = RDI[:, :, i]
            result = tracker.process_frame(frame)

            all_frame_results.append({
                "file": fname,
                "frame": i,
                "distance_safe": result["distance_safe"],
                "sitting": result["sitting"]
            })

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

    # 輸出逐幀結果
    csv_path = os.path.join(folder_path, "frame_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "frame", "distance_safe", "sitting"])
        for r in all_frame_results:
            writer.writerow([r["file"], r["frame"], r["distance_safe"], r["sitting"]])

    print(f"[INFO] Frame-by-frame results saved to: {csv_path}")


# ===============================================
# MAIN：執行流程
# ===============================================
if __name__ == "__main__":

    path_nopeople = r"C:\Users\clara\Desktop\毫米波雷達\dataset\no-people\nopeople.h5"

    # ⚠ 這裡只呼叫一次，拿到 bg + 門檻
    bg, sitting_threshold = load_background(path_nopeople)

    # 你要測的資料夾（60cm / 40cm / nopeople 都可以換這裡）
    folder_test   = r"C:\Users\clara\Desktop\test\test\5000frame\test_first50_5000_error"

    tracker = RadarStateTracker(bg, sitting_threshold, window_size=8)
    run_realtime_test_folder(folder_test, tracker)
