import h5py
import numpy as np


# =========================================
# 1. 讀取背景 (nopeople)
# =========================================
def load_background(nopeople_path):
    print("Loading nopeople background...")

    with h5py.File(nopeople_path, "r") as f:
        RDI_no = f["DS1"][0]              # shape = (32, 128, N)
        bg = np.mean(RDI_no, axis=2)      # (32,128) 平均背景模板

    print("Background loaded. Shape:", bg.shape)
    return bg


# =========================================
# 2. 從 RDI 框架中取得 residual peak bins
# =========================================
def compute_residual_peaks(file_path, bg):
    print(f"\nProcessing: {file_path}")

    with h5py.File(file_path, "r") as f:
        RDI = f["DS1"][0]    # shape = (32,128,N)

    peaks = []

    for i in range(RDI.shape[2]):
        frame = RDI[:, :, i]             # (32,128)
        residual = frame - bg            # 扣掉背景
        residual[residual < 0] = 0       # 去掉負值

        range_profile = np.max(residual, axis=1)   # (32,)

        if np.all(range_profile == 0):
            # 此幀沒有有意義的 foreground 訊號
            continue

        peak_bin = int(np.argmax(range_profile))
        peaks.append(peak_bin)

    if len(peaks) == 0:
        return None

    result = {
        "avg_peak_bin": float(np.mean(peaks)),
        "min_peak_bin": int(np.min(peaks)),
        "max_peak_bin": int(np.max(peaks)),
        "num_frames_used": len(peaks)
    }

    return result


# =========================================
# 3. 主流程：背景扣除 + 40cm / 60cm 分析
# =========================================
def analyze_distance(nopeople_path, path_40cm, path_60cm):

    # Step 1: 建立背景模板
    bg = load_background(nopeople_path)

    # Step 2: 分析 40cm residual peaks
    print("\n===== Analyzing 40cm dataset =====")
    res40 = compute_residual_peaks(path_40cm, bg)
    print(res40)

    # Step 3: 分析 60cm residual peaks
    print("\n===== Analyzing 60cm dataset =====")
    res60 = compute_residual_peaks(path_60cm, bg)
    print(res60)

    return res40, res60

def compute_avg_residual_profile(file_path, bg):

    with h5py.File(file_path, "r") as f:
        RDI = f["DS1"][0]

    profiles = []

    for i in range(RDI.shape[2]):
        frame = RDI[:, :, i]
        residual = frame - bg
        residual[residual < 0] = 0
        rp = np.max(residual, axis=1)   # range profile (32,)
        profiles.append(rp)

    return np.mean(profiles, axis=0)    # 平均 profile (32,)






# =========================================
# 4. 你只要設定三個檔案路徑即可
# =========================================
if __name__ == "__main__":

    path_nopeople = r"C:\Users\clara\Desktop\毫米波雷達\dataset\no-people\nopeople.h5"
    path_40cm     = r"C:\Users\clara\Desktop\毫米波雷達\dataset\40cm\40cm.h5"
    path_60cm     = r"C:\Users\clara\Desktop\毫米波雷達\dataset\60cm\60cm.h5"
    path_moving = r"C:\Users\clara\Desktop\毫米波雷達\dataset\move\moving.h5"
    path_small40cm=r"C:\Users\clara\Desktop\毫米波雷達\dataset\smaller_than_40cm\_0002_2025_11_24_20_53_29.h5"
    analyze_distance(path_nopeople, path_40cm, path_60cm)

    # ======== 使用 ========
    bg = load_background(path_nopeople)

    avg40 = compute_avg_residual_profile(path_40cm, bg)
    avg60 = compute_avg_residual_profile(path_60cm, bg)

    print("40cm profile =", avg40)
    print("60cm profile =", avg60)

    print("\n===== Analyzing moving dataset =====")
    avg_moving = compute_avg_residual_profile(path_moving, bg)
    print("moving profile =", avg_moving)
    print("moving avg residual =", np.mean(avg_moving))

    print("\n===== Analyzing smaller than 40cm dataset =====")
    avg_near = compute_avg_residual_profile(path_small40cm, bg)
    print("near profile =", avg_near)
    print("near avg residual =", np.mean(avg_near))




