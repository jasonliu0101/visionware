import h5py
import numpy as np

path = r"C:\Users\clara\Desktop\test\test\5000frame\test_first50_5000_correct\_0001_2025_11_25_20_54_14.h5"

with h5py.File(path, "r") as f:
    DS1 = f["DS1"][:]  # shape (2, R, D, N)
    RDI = DS1[0]
    R, D, N = RDI.shape
    peaks = []
    energies = []
    for i in range(N):
        rp = np.max(RDI[:, :, i], axis=1)
        peaks.append(np.argmax(rp))
        energies.append(np.max(rp))

    print("RDI shape =", (R, D, N))
    print("avg_peak_bin =", float(np.mean(peaks)))
    print("peak_bin_min =", int(np.min(peaks)))
    print("peak_bin_max =", int(np.max(peaks)))
    print("energy_min =", float(np.min(energies)))
    print("energy_max =", float(np.max(energies)))
