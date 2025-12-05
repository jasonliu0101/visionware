import h5py
import numpy as np

path = r"C:\Users\clara\Desktop\毫米波雷達\dataset\40cm\40cm.h5"

with h5py.File(path, "r") as f:
    RDI = f["DS1"][0]  # shape (32, 128, N)

energies = []

for i in range(1, RDI.shape[2]):
    diff = np.abs(RDI[:, :, i] - RDI[:, :, i-1])
    dynamic_profile = np.max(diff, axis=1)
    energies.append(np.sum(dynamic_profile))

print("min motion =", np.min(energies))
print("max motion =", np.max(energies))
print("avg motion =", np.mean(energies))
