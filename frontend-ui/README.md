# VisionWave Guardian — 前端介面

基於毫米波雷達的智慧視力與健康監測系統前端，搭配 Flask API 伺服器提供完整的即時監測體驗。

## 功能特色

### 即時監測
- **視距監測**：即時追蹤使用者與螢幕的距離，低於 40 公分即觸發警示
- **久坐監測**：追蹤連續坐姿時間，超過 30 分鐘提醒使用者起身活動

### 警示系統
- 頁面內視覺化警示通知
- 作業系統桌面通知（瀏覽器 Notification API）
- Web Audio API 音效提醒
- 完整的警示歷史記錄

### 統計分析
- 總監測時間追蹤
- 安全距離比例計算
- 警示次數統計
- 平均久坐時長分析
- 即時趨勢圖表（Chart.js）

### 介面設計
- 現代化玻璃擬態設計 (Glassmorphism)
- 流暢的動畫效果
- 響應式佈局（支援桌面、平板、手機）
- 深色主題配色
- 繁體中文介面

## 檔案結構

```
frontend-ui/
├── server.py         # Flask API 伺服器（整合雷達後端）
├── index.html        # 主要 HTML 結構
├── app.js            # 前端應用程式邏輯
├── style.css         # CSS 設計系統
├── start_server.sh   # 一鍵啟動腳本
└── README.md         # 本文件
```

## 使用方式

### 啟動伺服器

```bash
# 安裝依賴
pip install flask flask-cors

# 啟動
python3 server.py
```

伺服器啟動後，開啟瀏覽器訪問 **http://localhost:8000**

### 連接雷達後端

設定環境變數以啟用 RadarProcessor 即時處理：

```bash
export RADAR_BG_PATH=/path/to/nopeople_background.h5
export RADAR_CAL_PATH=/path/to/nopeople_folder/
python3 server.py
```

### 後端 API 規格

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/status` | GET | 取得目前感測狀態 |
| `/api/status` | POST | 手動更新狀態 |
| `/api/upload` | POST | 上傳 H5 檔案處理 |
| `/api/info` | GET | 系統資訊 |

**狀態 JSON 格式：**

```json
{
    "distance_safe": true,
    "sitting": false
}
```

## 瀏覽器支援

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 技術堆疊

- **HTML5** — 語意化標記
- **CSS3** — CSS Variables、Flexbox & Grid、Glassmorphism
- **JavaScript (ES6+)** — 非同步 API、狀態管理、Web Audio API
- **Chart.js 4.4** — 資料視覺化
- **Flask** — 後端 API 伺服器

## 開發團隊

**國立成功大學 成大一定隊**

劉冠宏 · 蕭品睿 · 李奕潔 · 李芷昀 · 鍾馥謙 · 卓芷妍 · 楊傑凱

指導教授：王維聰 博士

## 授權

© 2025 VisionWave Guardian — 國立成功大學 成大一定隊. All rights reserved.
