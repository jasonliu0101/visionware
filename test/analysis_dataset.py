import h5py
import os
import numpy as np
import matplotlib.pyplot as plt

def show_rdi_sample(folder_path, title_name):
    for filename in os.listdir(folder_path):
        if filename.endswith(".h5"):
            file_path = os.path.join(folder_path, filename)
            print(f"Loading {file_path}...")
            
            with h5py.File(file_path, "r") as f:
                if "DS1" not in f:
                    print("⚠️ DS1 not found in file, skip.")
                    continue
                
                DS1 = f["DS1"][:]   # shape (2, 32, 32, frames)
                RDI = DS1[0]       # 取第一張 map：RDI
                
                # 取第 0 幀
                frame0 = RDI[:, :, 0]
                
                # 顯示熱力圖
                plt.imshow(frame0, cmap='hot', interpolation='nearest')
                plt.colorbar()
                plt.title(f"{title_name} - RDI Heatmap (frame 0)")
                plt.show()
                
                return  # 只取第一個檔案的第一幀即可


# ===== 路徑 =====
move_path = r"C:\Users\clara\Desktop\毫米波雷達\dataset\move"
nopeople_path = r"C:\Users\clara\Desktop\毫米波雷達\dataset\no-people"
boundary40cm_path = r"C:\Users\clara\Desktop\毫米波雷達\dataset\40cm"

# ===== 顯示 Heatmap =====
show_rdi_sample(move_path, "Move")
show_rdi_sample(nopeople_path, "No People")
show_rdi_sample(boundary40cm_path, "40cm")
