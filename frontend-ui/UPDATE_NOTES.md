# VisionWave Guardian 更新說明

## 最新更新（2025-12-05 14:25）

### 🔄 主要變更

#### 1. 更快的輪詢頻率
- **從 3 秒改為 1 秒**
- 更即時的資料更新與反應
- 提供更好的使用體驗

#### 2. 修正視距顯示Bug
**問題**：不管 `distance_safe` 是 true 或 false 都顯示「距離過近」

**修正後邏輯**：
```javascript
if (!state.sitting) {
    // 沒人坐著 → 顯示「未偵測到使用者」
} else if (state.distance_safe) {
    // 有人坐著 且 距離安全 → 顯示「良好」
} else {
    // 有人坐著 但 距離過近 → 顯示「警告」
}
```

#### 3. 只在有人坐著時檢查距離
**重要邏輯變更**：
- 當 `sitting = false`（沒人坐著）時，**完全忽略** `distance_safe` 的值
- 因為沒人在位置上，檢查距離沒有意義
- 自動重置距離追蹤狀態和警示

```javascript
if (state.sitting) {
    // 有人坐著才檢查距離
    if (!state.distance_safe) {
        // 觸發距離警示邏輯...
    }
} else {
    // 沒人坐著，重置所有距離追蹤
    state.distanceUnsafeStartTime = null;
    dismissAlert('distance-alert');
}
```

#### 4. UI 平滑更新
**問題**：每次更新時頁面可能會閃爍或看起來在重新渲染

**解決方案**：
- 添加 CSS transitions 到所有動態元素
- 只更新變化的數值和進度條
- 不重新渲染整個組件

**CSS 改進**：
```css
.metric-value,
.metric-description,
.status-label {
    transition: opacity 150ms ease, color 150ms ease;
}
```

---

## 視距監測卡片狀態

### 狀態 1：未偵測到使用者
```
sitting = false
```
顯示：
- 狀態圈：灰色
- 標籤：「未偵測到使用者」
- 數值：「--」
- 進度條：0%（藍紫漸層）

### 狀態 2：安全距離
```
sitting = true
distance_safe = true
```
顯示：
- 狀態圈：綠色（safe）
- 標籤：「安全距離」
- 數值：「良好」
- 進度條：100%（綠色漸層）

### 狀態 3：距離過近
```
sitting = true
distance_safe = false
```
顯示：
- 狀態圈：紅色（danger，脈衝動畫）
- 標籤：「距離過近」
- 數值：「警告」
- 進度條：40%（紅色漸層）
- **10秒後觸發警示**

---

## 測試方式

使用遙控器測試所有場景：

### 測試 1：未偵測狀態
1. 開啟 `controller.html` 和 `index.html`
2. 在遙控器設定 `sitting = false`
3. **觀察**：視距卡片顯示「未偵測到使用者」
4. **驗證**：不管 `distance_safe` 設定什麼值都不影響顯示

### 測試 2：安全使用
1. 遙控器設定：`distance_safe = true`, `sitting = true`
2. **觀察**：視距卡片顯示「良好」，綠色指示器
3. **驗證**：無警示觸發

### 測試 3：距離過近警示
1. 遙控器設定：`distance_safe = false`, `sitting = true`
2. **觀察**：視距卡片立即顯示「警告」，紅色指示器
3. **等待 10 秒**
4. **驗證**：觸發距離警示通知
5. **繼續等待 15 秒**
6. **驗證**：警示重複出現

### 測試 4：離席自動重置
1. 先設定 `distance_safe = false`, `sitting = true` 觸發警示
2. 然後設定 `sitting = false`（模擬離席）
3. **驗證**：
   - 距離警示自動消失
   - 視距卡片顯示「未偵測到使用者」
   - 距離追蹤時間重置

---

## 效能優化

### 輪詢頻率
- **1 秒一次** API 呼叫
- 使用 `localStorage` 作為通訊橋樑（無網路延遲）
- CPU 占用極低

### UI 更新
- 只更新變化的 DOM 元素
- 使用 CSS transitions 而非 JavaScript 動畫
- 避免整頁重繪（reflow）

### 記憶體管理
- Chart 資料點限制在 30 個
- 警示歷史限制在 50 條
- 定期清理過期資料

---

## 更新的檔案

- ✅ `app.js` - 主邏輯文件
  - 改為 1 秒輪詢
  - 修正距離卡片顯示邏輯
  - 添加 sitting 狀態檢查

- ✅ `style.css` - 樣式文件
  - 添加平滑過渡效果
  - 優化動畫性能

---

## API 格式（再次確認）

後端務必**每次都回傳兩個欄位**：

```json
{
  "distance_safe": true,   // 距離是否安全 (>= 60cm)
  "sitting": false         // 是否偵測到有人坐著（不是久坐判斷）
}
```

**關鍵點**：
- `sitting` 只表示「有沒有人」，不是「有沒有久坐」
- `sitting = false` 時，前端會忽略 `distance_safe` 的值
- 久坐判斷完全由前端累積時間處理
