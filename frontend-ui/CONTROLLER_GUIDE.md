# 使用 API 遙控器測試前端

## 快速開始

### 步驟 1：開啟遙控器頁面
在瀏覽器中開啟：
```
file:///Users/jasonliu/visualwave/visionware/frontend-ui/controller.html
```

### 步驟 2：開啟主監測頁面
在**另一個瀏覽器分頁**中開啟：
```
file:///Users/jasonliu/visualwave/visionware/frontend-ui/index.html
```

### 步驟 3：開始測試
在遙控器頁面中：
- 切換「視距安全」開關
- 切換「久坐偵測」開關
- 或點擊快速場景按鈕

主監測頁面會**每 3 秒自動更新**，顯示您設定的狀態！

## 遙控器功能

### 手動控制開關
- **視距安全 (distance_safe)**
  - ON (綠色) = 距離安全
  - OFF (紅色) = 距離過近
  
- **久坐偵測 (sitting)**
  - ON (粉色) = 偵測到坐著
  - OFF (灰色) = 未偵測到

### 快速場景按鈕

1. **理想狀態** 🟢
   - distance_safe: `true`
   - sitting: `false`

2. **距離過近** 🟡
   - distance_safe: `false` ← 會觸發距離警示
   - sitting: `false`

3. **久坐中** 🟣
   - distance_safe: `true`
   - sitting: `true` ← 久坐計時器會開始計時

4. **危險狀態** 🔴
   - distance_safe: `false` ← 距離警示
   - sitting: `true` ← 久坐警示
   - 兩個警示會同時出現！

## 工作原理

```
controller.html (遙控器)
    ↓ 儲存設定到
localStorage
    ↑ 每 3 秒讀取
index.html (主頁面)
```

1. 遙控器將狀態存到 `localStorage`
2. 主頁面每 3 秒讀取 `localStorage`
3. 兩個頁面可以同時開啟，即時看到效果

## 測試建議

### 測試 1：距離警示
1. 開啟兩個頁面
2. 在遙控器點擊「距離過近」
3. 等待最多 3 秒
4. 主頁面應該出現紅色警示橫幅
5. 視距監測卡片顯示「警告」

### 測試 2：久坐警示
1. 在遙控器點擊「久坐中」
2. 觀察主頁面的久坐計時器開始計時
3. 久坐進度條會開始填充
4. （可選）等待 30 分鐘測試久坐警示

### 測試 3：組合場景
1. 在遙控器點擊「危險狀態」
2. 主頁面會同時顯示：
   - 距離過近警示
   - 久坐計時器
   - 兩個統計數據都更新

## 切換回模擬模式

如果想回到自動產生隨機資料的模式，編輯 `app.js`：

```javascript
const CONFIG = {
    API_ENDPOINT: 'SIMULATED',  // 改回 SIMULATED
    // ...
};
```

## 切換到真實後端

當後端 API 準備好後：

```javascript
const CONFIG = {
    API_ENDPOINT: 'http://localhost:5000/api/status',  // 真實的 API 端點
    // ...
};
```

## 注意事項

⚠️ **重要**：主頁面每 3 秒才會更新一次，所以在遙控器切換開關後，可能需要等待最多 3 秒才會在主頁面看到變化。

💡 **提示**：可以開啟瀏覽器的開發者工具 (F12)，查看 Console 訊息來確認資料傳輸狀態。
