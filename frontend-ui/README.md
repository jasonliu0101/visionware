# VisionWave Guardian 前端介面

基於毫米波雷達的智慧視力與健康監測系統前端介面。

## 功能特色

### 即時監測
- **視距監測**：即時追蹤使用者與螢幕的距離，確保保持安全的 60 公分以上距離
- **久坐監測**：追蹤連續坐姿時間，每 30 分鐘提醒使用者起身活動

### 警示系統
- 視覺化警示通知
- 距離過近警告
- 久坐時間超時提醒
- 可關閉的警示卡片
- 完整的警示歷史記錄

### 統計分析
- 總監測時間追蹤
- 安全距離比例計算
- 警示次數統計
- 平均久坐時長分析
- 互動式趨勢圖表（使用 Chart.js）

### 介面設計
- 現代化玻璃擬態設計 (Glassmorphism)
- 流暢的動畫效果
- 響應式佈局（支援桌面、平板、手機）
- 深色主題配色
- 繁體中文介面

## 檔案結構

```
frontend-ui/
├── index.html    # 主要 HTML 結構
├── style.css     # 完整的 CSS 設計系統
├── app.js        # JavaScript 應用程式邏輯
└── README.md     # 本文件
```

## 使用方式

### 1. 開啟介面

直接在瀏覽器中開啟 `index.html` 檔案：

```bash
# 在專案目錄中
open index.html
```

或使用 Python 快速啟動本地伺服器：

```bash
# Python 3
python3 -m http.server 8000

# 然後在瀏覽器中開啟 http://localhost:8000
```

### 2. 模擬模式（預設）

系統預設使用**模擬資料模式**，會自動生成測試資料來展示功能。這對於開發和測試非常有用。

### 3. 連接後端 API

當後端 API 準備好後，修改 `app.js` 中的設定：

```javascript
const CONFIG = {
    // 將 'SIMULATED' 改為實際的後端 API 端點
    API_ENDPOINT: 'http://localhost:5000/api/status',
    POLLING_INTERVAL: 2000, // 2 秒輪詢一次
    // ... 其他設定
};
```

### 後端 API 規格

後端應提供一個端點，返回以下 JSON 格式：

```json
{
    "distance_safe": true,   // 布林值：true = 安全距離，false = 距離過近
    "sitting": false         // 布林值：true = 正在坐著，false = 未偵測到
}
```

**範例響應：**

安全狀態：
```json
{
    "distance_safe": true,
    "sitting": false
}
```

需要警示：
```json
{
    "distance_safe": false,  // 距離過近
    "sitting": true          // 正在久坐
}
```

## 系統設定

在 `app.js` 的 `CONFIG` 物件中可調整以下參數：

```javascript
const CONFIG = {
    API_ENDPOINT: 'SIMULATED',              // API 端點
    POLLING_INTERVAL: 2000,                 // 輪詢間隔（毫秒）
    SITTING_WARNING_THRESHOLD: 30 * 60 * 1000,  // 久坐警告閾值（30分鐘）
    SITTING_DANGER_THRESHOLD: 40 * 60 * 1000,   // 久坐危險閾值（40分鐘）
    DISTANCE_WARNING_TIME: 10 * 1000,       // 距離警告時間（10秒）
    MAX_CHART_POINTS: 30,                   // 圖表最大資料點數
    MAX_HISTORY_ITEMS: 50                   // 最大歷史記錄數
};
```

## 瀏覽器支援

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

建議使用最新版本的現代瀏覽器以獲得最佳體驗。

## 技術堆疊

- **HTML5**：語意化標記
- **CSS3**：現代化設計系統
  - CSS Variables（自訂屬性）
  - Flexbox & Grid 佈局
  - Glassmorphism 效果
  - 流暢動畫與轉場
- **JavaScript (ES6+)**：
  - 非同步 API 呼叫
  - 即時資料更新
  - 狀態管理
- **Chart.js 4.4**：資料視覺化

## 開發團隊

國立成功大學 工業與資訊管理學系 第十一組
- R76131044 劉冠宏
- R76131036 蕭品睿
- R76131094 李奕潔
- R76131159 李芷昀
- R76121188 鍾馥謙
- R76131141 卓芷妍
- R76131117 楊傑凱

指導教授：王維聰 博士

## 授權

© 2025 VisionWave Guardian. All rights reserved.
