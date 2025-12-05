# VisionWave Guardian 警示邏輯更新說明

## 📋 更新概述

根據系統分析報告中的 Use Case 流程圖（Sequence Diagrams），本次更新重新實現了警示觸發邏輯，使其完全符合設計需求。

## 🔄 主要變更

### 1. API 格式說明

**後端 API 回傳格式：**
```json
{
  "distance_safe": true,  // 距離是否安全 (true = >= 60cm, false = < 60cm)
  "sitting": true         // 是否偵測到坐著 (true = 有人坐著, false = 未偵測到)
}
```

**重要說明：**
- `distance_safe`：後端回傳距離是否符合安全標準（>= 60cm）
- `sitting`：後端回傳是否偵測到使用者坐著，**這不是久坐判斷**
  - `true` = 雷達偵測到有人坐在位置上
  - `false` = 雷達未偵測到人（離席）
- **久坐判斷**：完全由前端根據 `sitting` 狀態自行累積時間來判斷

---

### 2. 視距警示邏輯（Distance Alert Logic）

#### 設計需求（參考 Use Case 1 流程圖）
1. 判斷距離是否 < 60cm 且持續 ≥ 10秒
2. 符合條件後觸發視距警示
3. 提醒使用者調整距離
4. 如果使用者忽略，每隔 15秒重複提醒
5. 使用者調整坐姿後，距離 >= 60cm → 解除警示

#### 實現方式

**狀態追蹤：**
```javascript
state.distance                    // 當前距離狀態（來自後端）
state.distanceUnsafeStartTime    // 距離不OK開始的時間戳
state.distanceUnsafeDuration     // 距離不OK持續時長（毫秒）
state.lastDistanceAlertTime      // 上次距離警示時間
```

**邏輯流程：**
```javascript
if (!state.distance) {  // 距離不OK (< 60cm)
    if (state.distanceUnsafeStartTime === null) {
        // 剛開始距離不OK → 記錄開始時間
        state.distanceUnsafeStartTime = now;
    } else {
        // 持續距離不OK → 累積時長
        state.distanceUnsafeDuration = now - state.distanceUnsafeStartTime;
    }
    
    if (state.distanceUnsafeDuration >= 10秒) {
        if (state.lastDistanceAlertTime === null) {
            // 第一次觸發警示
            showDistanceAlert();
            state.lastDistanceAlertTime = now;
        } else {
            // 檢查是否需要重複提醒（每15秒）
            timeSinceLastAlert = now - state.lastDistanceAlertTime;
            if (timeSinceLastAlert >= 15秒) {
                showDistanceAlert();  // 重複提醒
                state.lastDistanceAlertTime = now;
            }
        }
    }
} else {  // 距離OK
    // 重置所有追蹤狀態
    state.distanceUnsafeStartTime = null;
    state.distanceUnsafeDuration = 0;
    state.lastDistanceAlertTime = null;
    dismissAlert('distance-alert');  // 解除警示
}
```

**配置參數：**
```javascript
DISTANCE_UNSAFE_TRIGGER: 10 * 1000,   // 10秒：持續10秒才觸發
DISTANCE_ALERT_REPEAT: 15 * 1000,     // 15秒：每15秒重複提醒
```

---

### 3. 久坐警示邏輯（Sitting Alert Logic）

#### 設計需求（參考 Use Case 2 流程圖）
1. 判斷是否久坐 ≥ 30 分鐘
2. 持續監測與累積坐著時間
3. 符合條件後觸發久坐警示
4. 提醒使用者起身休息
5. 如果使用者忽略，每隔 10 分鐘重複提醒
6. 使用者離席 (sitting = false) → 解除警示並重置計時

#### 實現方式

**狀態追蹤：**
```javascript
state.sitting                 // 當前坐著狀態（來自後端）
state.sittingStartTime        // 開始坐著的時間戳
state.sittingTotalDuration    // 累積坐著時長（毫秒）
state.lastSittingAlertTime    // 上次久坐警示時間
```

**邏輯流程：**
```javascript
if (state.sitting) {  // 偵測到坐著
    if (state.sittingStartTime === null) {
        // 剛開始坐下 → 記錄開始時間
        state.sittingStartTime = now;
    } else {
        // 持續坐著 → 累積時長
        state.sittingTotalDuration = now - state.sittingStartTime;
    }
    
    if (state.sittingTotalDuration >= 30分鐘) {
        if (state.lastSittingAlertTime === null) {
            // 第一次觸發警示
            showSittingAlert();
            state.lastSittingAlertTime = now;
        } else {
            // 檢查是否需要重複提醒（每10分鐘）
            timeSinceLastAlert = now - state.lastSittingAlertTime;
            if (timeSinceLastAlert >= 10分鐘) {
                showSittingAlert();  // 重複提醒
                state.lastSittingAlertTime = now;
            }
        }
    }
} else {  // 未偵測到（離席）
    // 重置所有追蹤狀態
    state.sittingStartTime = null;
    state.sittingTotalDuration = 0;
    state.lastSittingAlertTime = null;
    dismissAlert('sitting-alert');  // 解除警示
}
```

**配置參數：**
```javascript
SITTING_TRIGGER: 30 * 60 * 1000,      // 30分鐘：久坐超過30分鐘才觸發
SITTING_ALERT_REPEAT: 10 * 60 * 1000, // 10分鐘：每10分鐘重複提醒
```

---

## 📊 與舊邏輯的對比

| 項目 | 舊邏輯 | 新邏輯 |
|------|--------|--------|
| **視距判斷** | 距離不OK立即警示 | 距離不OK持續**10秒**才觸發 |
| **視距重複提醒** | 無系統化重複機制 | 每**15秒**重複提醒 |
| **久坐判斷** | 後端回傳久坐狀態（假設） | **前端自行累積時間**判斷 |
| **久坐觸發閾值** | 30分鐘 | **30分鐘**（維持） |
| **久坐重複提醒** | 無系統化重複機制 | 每**10分鐘**重複提醒 |
| **警示解除** | 手動關閉或超時自動消失 | 條件恢復後**自動解除** |

---

## 🔧 受影響的檔案

### 主要邏輯檔案

#### `app.js` （主要修改）
- 更新 `state` 結構，新增追蹤欄位
- 更新 `CONFIG` 配置，移除舊閾值
- 完全重寫 `checkHealth()` 函數
- 新增 `showDistanceAlert()` 和 `showSittingAlert()` 函數
- 移除舊的 `checkAlerts()` 函數
- 更新所有 UI 函數以使用新的 state 屬性

#### `controller.js` （格式同步）
- 更新 state 格式：`distance_safe` → `distance`
- 更新所有相關函數和顯示邏輯

#### `controller.html` （UI更新）
- 更新標籤文字：`distance_safe` → `distance`
- 更新 JSON 顯示範例

---

## ✅ 功能驗證清單

- [x] 距離不OK持續10秒後觸發警示
- [x] 距離警示每15秒重複提醒
- [x] 距離OK時自動解除警示
- [x] 久坐30分鐘後觸發警示
- [x] 久坐警示每10分鐘重複提醒
- [x] 離席時自動解除久坐警示
- [x] 控制器頁面使用新API格式
- [x] 主頁面正確讀取新API格式
- [x] UI正確顯示所有狀態

---

## 🧪 測試方法

### 測試 1：視距警示觸發
1. 開啟遙控器和主頁面
2. 在遙控器設定「距離過近」（distance = false）
3. **等待 10 秒** → 應該出現視距警示
4. **繼續等待 15 秒** → 應該再次出現警示（重複提醒）
5. 在遙控器設定「理想狀態」（distance = true）→ 警示應自動消失

### 測試 2：久坐警示觸發
1. 在遙控器設定「久坐中」（sitting = true）
2. 觀察久坐計時器開始計時
3. **等待 30 分鐘**（或修改 `CONFIG.SITTING_TRIGGER` 為較短時間測試）→ 應該出現久坐警示
4. **繼續等待 10 分鐘** → 應該再次出現警示（重複提醒）
5. 在遙控器設定 sitting = false → 警示應自動消失，計時器歸零

### 測試 3：組合場景
1. 在遙控器設定「危險狀態」（distance = false, sitting = true）
2. 應該同時追蹤距離和久坐時間
3. 距離警示應在 10 秒後觸發，每 15 秒重複
4. 久坐警示應在 30 分鐘後觸發，每 10 分鐘重複

---

## 📝 後端整合說明

### API 回傳格式（最終確認）

```json
{
  "distance_safe": true,   // true = 距離安全 (>= 60cm), false = 距離過近 (< 60cm)
  "sitting": false         // true = 偵測到有人坐著, false = 未偵測到人
}
```

### 重要說明

**`distance_safe` 欄位：**
- 後端判斷距離是否符合安全標準（>= 60cm）
- `true` = 距離安全，符合要求
- `false` = 距離過近，不符合要求

**`sitting` 欄位：**
- 後端回傳雷達是否偵測到有人坐在位置上
- **這不是久坐判斷！** 只是「有沒有人」的偵測結果
- `true` = 雷達偵測到有人坐著
- `false` = 雷達未偵測到人（離席、站起來等）
- **久坐的判斷由前端自己累積時間計算**

### 前端處理邏輯

```javascript
// 視距警示：使用 distance_safe 欄位
if (!state.distance_safe) {
    // 距離不安全 → 開始追蹤時長 → 10秒後觸發警示
}

// 久坐警示：使用 sitting 欄位
if (state.sitting) {
    // 有人坐著 → 累積坐著時間 → 30分鐘後觸發久坐警示
} else {
    // 沒人坐著（離席）→ 重置久坐計時
}
```

### 範例場景

**場景 1：正常使用**
```json
{"distance_safe": true, "sitting": true}
```
- 距離OK，有人坐著
- **前端**：不觸發距離警示，開始累積坐著時間

**場景 2：距離過近**
```json
{"distance_safe": false, "sitting": true}
```
- 距離不OK，有人坐著
- **前端**：觸發距離警示（10秒後），同時累積坐著時間

**場景 3：離席**
```json
{"distance_safe": true, "sitting": false}
```
- 距離OK（無意義，因為沒人），沒人坐著
- **前端**：重置久坐計時器

**場景 4：久坐但距離OK**
```json
{"distance_safe": true, "sitting": true}
```
持續30分鐘後：
- 距離OK（不觸發距離警示）
- 但**前端累積時間超過30分鐘** → **觸發久坐警示**

### 後端開發注意事項

1. **每次都必須回傳兩個欄位**：`distance_safe` 和 `sitting`
2. **sitting 不需要判斷久坐**：只需回傳「有沒有偵測到人」
3. **時間累積由前端處理**：後端不需要追蹤坐著多久
4. **輪詢頻率**：前端每3秒呼叫一次API

---

## 🎯 設計優勢

1. **符合需求規格**：完全按照 Use Case 流程圖實現
2. **避免誤報**：10秒延遲避免短暫靠近螢幕就觸發警示
3. **持續提醒**：重複警示機制確保使用者不會忽略
4. **自動恢復**：條件改善後自動解除，無需手動操作
5. **前端獨立**：久坐判斷邏輯在前端，減少後端負擔
6. **易於調整**：所有時間閾值集中在 `CONFIG` 中，方便調整

---

## 🔗 相關文件

- [CONTROLLER_GUIDE.md](file:///Users/jasonliu/visualwave/visionware/frontend-ui/CONTROLLER_GUIDE.md) - 遙控器使用說明
- [README.md](file:///Users/jasonliu/visualwave/visionware/frontend-ui/README.md) - 前端使用說明
- [walkthrough.md](file:///Users/jasonliu/.gemini/antigravity/brain/5c7e0304-26ed-4b19-904b-1b5a5d49468d/walkthrough.md) - 完整開發報告
