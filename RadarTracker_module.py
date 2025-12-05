import os
import h5py
import numpy as np
from collections import deque

# ===============================================
# 輔助函式 (Helper Functions)
# ===============================================
def load_background(nopeople_path):
    # ... (與您提供的 load_background 函式內容相同) ...
    print("[INFO] Loading background from nopeople...")
    with h5py.File(nopeople_path, "r") as f:
        RDI_no = f["DS1"][0]              # shape (32,128,N)
        bg = np.mean(RDI_no, axis=2)      # (32,128)
    print("[INFO] Background loaded.")
    return bg

def compute_residual_profile(frame, bg):
    # ... (與您提供的 compute_residual_profile 函式內容相同) ...
    residual = frame - bg
    residual[residual < 0] = 0
    range_profile = np.max(residual, axis=1)  # (32,)
    return range_profile


# ===============================================
# 主要處理器類別 (Main Processor Class)
# ===============================================
class RadarProcessor:
    
    def __init__(self, bg_path: str, calibration_folder_path: str, window_size: int = 8):
        """
        初始化雷達狀態追蹤器，載入背景並執行動態校準。
        """
        # 1. 載入背景
        self.bg = load_background(bg_path)
        
        # 2. 初始化核心追蹤器
        self.tracker = self._initialize_tracker(window_size)
        
        # 3. 執行校準
        self._run_calibration(calibration_folder_path)


    def _initialize_tracker(self, window_size):
        """
        將 RadarStateTracker 的邏輯封裝在內部，避免外部直接操作其複雜屬性。
        """
        class _RadarStateTracker:
            # 將您原本 RadarStateTracker 類別的所有方法和屬性放在這裡
            
            def __init__(self, bg, window_size=8):
                # 屬性初始化（與您提供的程式碼一致）
                self.bg = bg
                self.history = deque(maxlen=window_size)
                self.window_size = window_size
                self.STD_THRESHOLD = 0.0003
                self.AVG_THRESHOLD_FOR_SITTING = None 
                self.calibration_data = []             
                
                # 統計計數等所有其他屬性也應該放在這裡
                self.count_distance_safe_true = 0
                self.count_distance_safe_false = 0
                self.count_sitting_true = 0
                self.count_sitting_false = 0
                # ... (省略所有連續事件計數的屬性) ...
                self.consecutive_true = 0
                self.consecutive_false = 0
                self.has_true_285 = False
                self.has_false_285 = False
                self.count_true_285_events = 0
                self.count_false_285_events = 0
                self.true_event_lock = False
                self.false_event_lock = False

            # 將您原本的 reset_single_file_stats 搬移到這裡
            def reset_single_file_stats(self):
                # ... 內容與您提供的程式碼相同 ...
                self.count_distance_safe_true  = 0
                self.count_distance_safe_false = 0
                self.count_sitting_true        = 0
                self.count_sitting_false       = 0
                self.consecutive_true = 0
                self.consecutive_false = 0
                self.true_event_lock = False
                self.false_event_lock = False


            # 將您原本的 calibrate_avg_threshold 搬移到這裡
            def calibrate_avg_threshold(self, k=3):
                # ... 內容與您提供的程式碼相同 ...
                if not self.calibration_data:
                    self.AVG_THRESHOLD_FOR_SITTING = 0.005
                    return

                data = np.array(self.calibration_data)
                mu = np.mean(data)
                sigma = np.std(data)
                new_threshold = mu + k * sigma
                self.AVG_THRESHOLD_FOR_SITTING = max(new_threshold, 0.001) 
                print(f"[INFO] Set AVG_THRESHOLD_FOR_SITTING = {self.AVG_THRESHOLD_FOR_SITTING:.6f} (k={k})")
                self.calibration_data.clear()

            # 將您原本的 process_frame 搬移到這裡
            def process_frame(self, frame, is_calibrating=False):
                # ... (您的 process_frame 邏輯) ...
                
                # Step 1-3: 計算 window_avg, window_std
                rp = compute_residual_profile(frame, self.bg)
                avg_val = float(np.mean(rp))
                self.history.append(avg_val)

                if len(self.history) < self.window_size:
                    if is_calibrating: return None 
                    return {"distance_safe": True, "sitting": True} # 簡化後的回傳

                window_avg = np.mean(self.history)
                window_std = np.std(self.history)
                
                if is_calibrating:
                    self.calibration_data.append(window_avg)
                    return None 

                # 確保已校準
                avg_thresh = self.AVG_THRESHOLD_FOR_SITTING if self.AVG_THRESHOLD_FOR_SITTING is not None else 0.005

                # Sitting 判斷
                sitting = False 
                if window_avg > avg_thresh and window_std > self.STD_THRESHOLD:
                    sitting = True
                
                # Distance Safe 判斷
                distance_safe = False if window_avg > 0.06 else True

                # ===== 統計更新 (簡化版本，只保留核心輸出) =====
                # 這裡需要保留統計更新的程式碼，因為它們更新了 self.count_... 等狀態

                # Distance Safe 統計
                if distance_safe: self.count_distance_safe_true += 1
                else: self.count_distance_safe_false += 1

                # 連續次數統計
                if distance_safe: 
                    self.consecutive_true += 1
                    self.consecutive_false = 0
                else: 
                    self.consecutive_false += 1
                    self.consecutive_true = 0

                # 285 次事件統計 (保持不變)
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

                # Sitting 統計
                if sitting: self.count_sitting_true += 1
                else: self.count_sitting_false += 1

                # 返回簡化後的輸出格式
                return {
                    "distance_safe": distance_safe,
                    "sitting": sitting,
                }
        
        # 返回內部追蹤器實例
        return _RadarStateTracker(self.bg, window_size)


    def _run_calibration(self, nopeople_folder_path: str):
        """
        執行動態校準，與您原有的 run_calibration 邏輯類似。
        """
        print("\n[INFO] Starting AVG threshold calibration...")
        files = [f for f in os.listdir(nopeople_folder_path) if f.endswith(".h5")]
        if not files:
            print(f"[ERROR] No .h5 files found for calibration in: {nopeople_folder_path}")
            self.tracker.calibrate_avg_threshold(k=3)
            return

        fpath = os.path.join(nopeople_folder_path, files[0])
        with h5py.File(fpath, "r") as f:
            RDI = f["DS1"][0]

        self.tracker.history.clear()
        
        for i in range(RDI.shape[2]):
            frame = RDI[:, :, i]
            # 呼叫內部 tracker 的校準模式
            self.tracker.process_frame(frame, is_calibrating=True) 

        self.tracker.calibrate_avg_threshold(k=3)
        print("[INFO] Calibration finished.")
        

    def get_state(self, frame: np.ndarray) -> dict:
        """
        【外部模組調用點】
        處理單一雷達幀並返回狀態。
        """
        # 呼叫內部 tracker 的 process_frame，並返回結果
        return self.tracker.process_frame(frame, is_calibrating=False)


    def get_statistics(self) -> dict:
        """
        可選：提供獲取累積統計數據的接口。
        """
        return {
            "total_distance_safe_true": self.tracker.count_distance_safe_true,
            "total_distance_safe_false": self.tracker.count_distance_safe_false,
            "total_sitting_true": self.tracker.count_sitting_true,
            "total_sitting_false": self.tracker.count_sitting_false,
            "has_true_285": self.tracker.has_true_285,
            "has_false_285": self.tracker.has_false_285,
            "count_true_285_events": self.tracker.count_true_285_events,
            "count_false_285_events": self.tracker.count_false_285_events,
        }
   