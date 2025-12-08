// =====================================
// VisionWave Guardian - Main Application
// =====================================

// Global State
const state = {
    // Backend data
    distance_safe: true,   // true = 距離安全 (>= 40cm), false = 距離過近 (< 40cm)
    sitting: false,        // true = 偵測到坐著, false = 未偵測到（注意：這不是久坐判斷）

    // Distance tracking
    distanceUnsafeStartTime: null,  // 距離不OK開始的時間
    distanceUnsafeDuration: 0,      // 距離不OK持續時長（毫秒）
    lastDistanceAlertTime: null,    // 上次距離警示時間

    // Sitting tracking
    sittingStartTime: null,         // 開始坐著的時間
    sittingTotalDuration: 0,        // 累積坐著時長（毫秒）
    lastSittingAlertTime: null,     // 上次久坐警示時間

    // Statistics
    totalMonitoringTime: 0,
    alertCount: 0,
    safeDistanceCount: 0,
    totalChecks: 0,
    alertHistory: [],

    // Chart data
    chartData: {
        labels: [],
        distanceData: [],
        sittingData: []
    }
};

// Configuration
const CONFIG = {
    // API Mode: 'CONTROLLER' (遙控器), 'SIMULATED' (模擬), 'FUNCTION' (自定義函數), or URL string (真實API)
    API_ENDPOINT: 'CONTROLLER',
    POLLING_INTERVAL: 1000, // 1 second (更頻繁的更新以獲得更好的即時性)

    // Distance alert thresholds
    DISTANCE_UNSAFE_TRIGGER: 0,              // 0秒：一偵測到距離不安全就立即觸發警示
    DISTANCE_ALERT_REPEAT: 15 * 1000,        // 15秒：警示後每15秒重複提醒

    // Sitting alert thresholds  
    SITTING_TRIGGER: 30 * 60 * 1000,         // 30分鐘：久坐超過30分鐘才觸發警示
    SITTING_ALERT_REPEAT: 10 * 60 * 1000,    // 10分鐘：警示後每10分鐘重複提醒

    // Sound settings
    SOUND_ENABLED: true,                     // 啟用提醒音效

    // Other settings
    MAX_CHART_POINTS: 60,          // 60 點 × 10 秒間隔 = 10 分鐘範圍
    CHART_UPDATE_INTERVAL: 10000,  // 每 10 秒才記錄一個圖表數據點
    MAX_HISTORY_ITEMS: 50
};

// Chart instance
let healthChart = null;
let lastChartUpdateTime = 0;  // 上次更新圖表的時間

// =====================================
// Initialization
// =====================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 VisionWave Guardian 啟動中...');

    // 設置歡迎頁面的進入系統按鈕
    const landingOverlay = document.getElementById('landing-overlay');
    const enterSystemBtn = document.getElementById('enter-system-btn');

    // 檢查是否已經進入過系統
    const hasEnteredSystem = localStorage.getItem('visionwave_system_entered');

    if (hasEnteredSystem) {
        // 已經進入過，直接隱藏歡迎頁面
        landingOverlay.classList.add('hidden');
        setTimeout(() => {
            landingOverlay.style.display = 'none';
        }, 500);
    }

    // 進入系統按鈕點擊事件
    enterSystemBtn.addEventListener('click', () => {
        console.log('✅ 使用者點擊進入系統');

        // 初始化音效系統（需要使用者互動）
        initAudioContext();

        // 播放歡迎音效
        playAlertSound('success');

        // 標記已進入系統
        localStorage.setItem('visionwave_system_entered', 'true');

        // 隱藏歡迎頁面
        landingOverlay.classList.add('hidden');
        setTimeout(() => {
            landingOverlay.style.display = 'none';
        }, 500);
    });

    initializeChart();
    requestNotificationPermission();
    startMonitoring();
    startTimer();

    // 監聽測試警示觸發器
    window.addEventListener('storage', (e) => {
        if (e.key === 'visionwave_test_sitting_alert') {
            console.log('🧪 收到測試久坐警示觸發');
            // 立即觸發久坐警示（不論實際久坐時間）
            const testMinutes = Math.floor((state.sittingTotalDuration || 0) / 60000) || 30; // 預設顯示30分鐘
            const alertMessage = `您已經坐著 ${testMinutes} 分鐘了，建議起身休息、伸展一下。`;

            // 播放提醒音效
            playAlertSound('sitting');

            // 顯示頁面內警示
            showAlert('warning', '久坐提醒', alertMessage, 'sitting-alert-test');

            // 顯示瀏覽器原生通知
            showBrowserNotification('⏰ 久坐提醒', alertMessage, 'sitting');

            // 清除測試標誌
            localStorage.removeItem('visionwave_test_sitting_alert');
        }
    });
});

// =====================================
// Simulated API
// =====================================

function simulateAPIResponse() {
    // Simulate realistic behavior patterns
    const now = Date.now();

    // Simulate distance safe most of the time (90% chance)
    const distance_safe = Math.random() > 0.1;

    // Simulate sitting pattern - more likely to be sitting during work hours
    const sitting = Math.random() > 0.3;

    return {
        distance_safe: distance_safe,  // true = 距離安全, false = 距離過近
        sitting: sitting               // true = 偵測到坐著, false = 未偵測到
    };
}

async function fetchHealthData() {
    if (CONFIG.API_ENDPOINT === 'CONTROLLER') {
        // Read from controller page via localStorage
        try {
            const stateJson = localStorage.getItem('visionwave_api_state');
            if (stateJson) {
                return JSON.parse(stateJson);
            } else {
                // Default state if controller hasn't been opened yet
                return {
                    distance_safe: true,
                    sitting: false
                };
            }
        } catch (error) {
            console.error('❌ 讀取遙控器資料失敗:', error);
            return {
                distance_safe: true,
                sitting: false
            };
        }
    } else if (CONFIG.API_ENDPOINT === 'SIMULATED') {
        // Return simulated data
        return new Promise(resolve => {
            setTimeout(() => {
                resolve(simulateAPIResponse());
            }, 100);
        });
    } else if (CONFIG.API_ENDPOINT === 'FUNCTION') {
        // Call custom function directly
        try {
            // 假設您的函數掛載在 window 物件上，例如 window.getSensorData()
            // 請將 getSensorData 替換為您實際的函數名稱
            if (typeof window.getSensorData === 'function') {
                const data = await window.getSensorData();
                return data;
            } else {
                console.warn('⚠️ 找不到 window.getSensorData 函數，請確認已定義');
                // 回傳預設安全狀態避免報錯
                return {
                    distance_safe: true,
                    sitting: false
                };
            }
        } catch (error) {
            console.error('❌ 呼叫自定義函數失敗:', error);
            return null;
        }
    } else {
        // Actual API call
        try {
            const response = await fetch(CONFIG.API_ENDPOINT);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('❌ API 呼叫失敗:', error);
            showSystemError();
            return null;
        }
    }
}

// =====================================
// Monitoring Logic
// =====================================

async function startMonitoring() {
    console.log('👁️ 開始監測...');

    // Initial check
    await checkHealth();

    // Set up polling
    setInterval(async () => {
        await checkHealth();
    }, CONFIG.POLLING_INTERVAL);
}

async function checkHealth() {
    const data = await fetchHealthData();

    if (!data) return;

    state.totalChecks++;
    const now = Date.now();

    // Store previous state
    const previousDistanceSafe = state.distance_safe;
    const previousSitting = state.sitting;

    // Update current state from backend
    state.distance_safe = data.distance_safe;  // 後端回傳：距離是否安全
    state.sitting = data.sitting;              // 後端回傳：是否偵測到坐著（不是久坐判斷）

    // Track statistics
    if (state.distance_safe) {
        state.safeDistanceCount++;
    }

    // =====================================
    // 視距監測邏輯 (Distance Monitoring)
    // 重要：只有當使用者坐著時才檢查距離
    // =====================================

    if (state.sitting) {
        // 有人坐著才檢查距離

        if (!state.distance_safe) {
            // 距離不OK (< 40cm)

            if (state.distanceUnsafeStartTime === null) {
                // 剛開始距離不OK，記錄開始時間
                state.distanceUnsafeStartTime = now;
                state.distanceUnsafeDuration = 0;
            } else {
                // 持續距離不OK，累積時長
                state.distanceUnsafeDuration = now - state.distanceUnsafeStartTime;
            }

            // 判斷是否需要觸發警示
            if (state.distanceUnsafeDuration >= CONFIG.DISTANCE_UNSAFE_TRIGGER) {
                // 已持續 >= 10秒

                if (state.lastDistanceAlertTime === null) {
                    // 第一次觸發警示
                    showDistanceAlert();
                    state.lastDistanceAlertTime = now;
                } else {
                    // 檢查是否需要重複提醒（每15秒）
                    const timeSinceLastAlert = now - state.lastDistanceAlertTime;
                    if (timeSinceLastAlert >= CONFIG.DISTANCE_ALERT_REPEAT) {
                        showDistanceAlert();
                        state.lastDistanceAlertTime = now;
                    }
                }
            }

        } else {
            // 距離OK，重置追蹤
            state.distanceUnsafeStartTime = null;
            state.distanceUnsafeDuration = 0;
            state.lastDistanceAlertTime = null;

            // 解除警示
            dismissAlert('distance-alert');
        }
    } else {
        // 沒人坐著，重置距離追蹤（因為不需要檢查距離）
        state.distanceUnsafeStartTime = null;
        state.distanceUnsafeDuration = 0;
        state.lastDistanceAlertTime = null;
        dismissAlert('distance-alert');
    }

    // =====================================
    // 久坐監測邏輯 (Sitting Monitoring)
    // =====================================

    if (state.sitting) {
        // 偵測到坐著

        if (state.sittingStartTime === null) {
            // 剛開始坐下，記錄開始時間
            state.sittingStartTime = now;
            state.sittingTotalDuration = 0;
        } else {
            // 持續坐著，累積時長
            state.sittingTotalDuration = now - state.sittingStartTime;
        }

        // 判斷是否需要觸發警示
        if (state.sittingTotalDuration >= CONFIG.SITTING_TRIGGER) {
            // 已久坐 >= 30分鐘

            if (state.lastSittingAlertTime === null) {
                // 第一次觸發警示
                showSittingAlert();
                state.lastSittingAlertTime = now;
            } else {
                // 檢查是否需要重複提醒（每10分鐘）
                const timeSinceLastAlert = now - state.lastSittingAlertTime;
                if (timeSinceLastAlert >= CONFIG.SITTING_ALERT_REPEAT) {
                    showSittingAlert();
                    state.lastSittingAlertTime = now;
                }
            }
        }

    } else {
        // 未偵測到坐著（離席），重置追蹤
        state.sittingStartTime = null;
        state.sittingTotalDuration = 0;
        state.lastSittingAlertTime = null;

        // 解除警示
        dismissAlert('sitting-alert');
    }

    // Update UI
    updateUI();

    // Update chart
    updateChartData();
}

// =====================================
// Sound Notification System
// =====================================

// Audio Context for playing sounds
let audioContext = null;

// Initialize Audio Context (requires user interaction on some browsers)
function initAudioContext() {
    if (!audioContext) {
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('🔊 音效系統已初始化');
        } catch (error) {
            console.error('❌ 無法初始化音效系統:', error);
        }
    }
    return audioContext;
}

// Play alert sound using Web Audio API
function playAlertSound(type = 'warning') {
    if (!CONFIG.SOUND_ENABLED) return;

    const ctx = initAudioContext();
    if (!ctx) return;

    try {
        // Resume audio context if it's suspended (browser autoplay policy)
        if (ctx.state === 'suspended') {
            ctx.resume();
        }

        const now = ctx.currentTime;
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        // Different sounds for different alert types
        if (type === 'distance') {
            // 距離警示：急促的警告音 (較高頻)
            oscillator.frequency.setValueAtTime(800, now);
            oscillator.frequency.setValueAtTime(600, now + 0.1);
            oscillator.frequency.setValueAtTime(800, now + 0.2);

            gainNode.gain.setValueAtTime(0.3, now);
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.3);

            oscillator.start(now);
            oscillator.stop(now + 0.3);
        } else if (type === 'sitting') {
            // 久坐提醒：柔和的提示音 (雙音調)
            oscillator.frequency.setValueAtTime(523.25, now); // C5
            oscillator.frequency.setValueAtTime(659.25, now + 0.15); // E5
            oscillator.frequency.setValueAtTime(783.99, now + 0.3); // G5

            gainNode.gain.setValueAtTime(0.2, now);
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

            oscillator.start(now);
            oscillator.stop(now + 0.5);
        } else if (type === 'success') {
            // 成功音：愉悅的上升音
            oscillator.frequency.setValueAtTime(523.25, now); // C5
            oscillator.frequency.setValueAtTime(659.25, now + 0.1); // E5

            gainNode.gain.setValueAtTime(0.15, now);
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.25);

            oscillator.start(now);
            oscillator.stop(now + 0.25);
        }

        oscillator.onended = () => {
            oscillator.disconnect();
            gainNode.disconnect();
        };

    } catch (error) {
        console.error('❌ 播放音效失敗:', error);
    }
}

// =====================================
// Browser Notification System
// =====================================

function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.warn('⚠️ 此瀏覽器不支援桌面通知功能');
        return;
    }

    if (Notification.permission === 'default') {
        // 首次請求權限
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                console.log('✅ 通知權限已授予');
                // 記錄已經顯示過歡迎通知
                localStorage.setItem('visionwave_notification_welcomed', 'true');
                // 播放成功音效
                playAlertSound('success');
                // 顯示歡迎通知（只有首次授權時才顯示）
                showBrowserNotification(
                    '✅ VisionWave Guardian',
                    '通知功能已啟用，我們將在需要時提醒您！',
                    'success'
                );
            } else {
                console.log('❌ 通知權限被拒絕');
            }
        });
    } else if (Notification.permission === 'granted') {
        console.log('✅ 通知權限已存在');
        // 不再重複顯示歡迎通知
    } else {
        console.log('❌ 通知權限被拒絕');
    }
}

function showBrowserNotification(title, message, type = 'alert') {
    // 檢查瀏覽器是否支援通知
    if (!('Notification' in window)) {
        return;
    }

    // 檢查權限
    if (Notification.permission !== 'granted') {
        return;
    }

    // 設定通知選項
    const options = {
        body: message,
        icon: getNotificationIcon(type),
        badge: '/favicon.ico',
        tag: type === 'distance' ? 'distance-alert' : type === 'sitting' ? 'sitting-alert' : 'general',
        requireInteraction: type !== 'success', // 成功通知自動消失，警示需要用戶互動
        vibrate: type !== 'success' ? [200, 100, 200] : undefined,
        timestamp: Date.now(),
        silent: false
    };

    // 創建並顯示通知
    try {
        const notification = new Notification(title, options);

        // 點擊通知時，聚焦到視窗
        notification.onclick = () => {
            window.focus();
            notification.close();
        };

        // 自動關閉通知（除非需要互動）
        if (type === 'success') {
            setTimeout(() => notification.close(), 5000);
        } else {
            setTimeout(() => notification.close(), 15000);
        }
    } catch (error) {
        console.error('❌ 無法顯示通知:', error);
    }
}

function getNotificationIcon(type) {
    // 根據通知類型返回不同的 emoji 圖示
    // 注意：在實際應用中，這裡應該使用圖片 URL
    switch (type) {
        case 'distance':
            return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">⚠️</text></svg>';
        case 'sitting':
            return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">⏰</text></svg>';
        case 'success':
            return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">✅</text></svg>';
        default:
            return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🔔</text></svg>';
    }
}

// =====================================
// Alert Functions
// =====================================

function showDistanceAlert() {
    const alertMessage = '您與螢幕的距離過近！請保持至少 40 公分的安全距離，以保護視力健康。';

    // 播放警示音效
    playAlertSound('distance');

    // 顯示頁面內警示
    showAlert('danger', '視距警示', alertMessage, 'distance-alert');

    // 顯示瀏覽器原生通知
    showBrowserNotification('⚠️ 視距警示', alertMessage, 'distance');
}

function showSittingAlert() {
    const minutes = Math.floor(state.sittingTotalDuration / 60000);
    const alertMessage = `您已經坐著 ${minutes} 分鐘了，建議起身休息、伸展一下。`;

    // 播放提醒音效
    playAlertSound('sitting');

    // 顯示頁面內警示
    showAlert('warning', '久坐提醒', alertMessage, 'sitting-alert');

    // 顯示瀏覽器原生通知
    showBrowserNotification('⏰ 久坐提醒', alertMessage, 'sitting');
}




// =====================================
// UI Updates
// =====================================

function updateUI() {
    updateDistanceCard();
    updateSittingCard();
    updateStatistics();
}

function updateDistanceCard() {
    const statusCircle = document.querySelector('#distance-card .status-circle');
    const statusLabel = document.querySelector('#distance-card .status-label');
    const metricValue = document.querySelector('#distance-value');
    const progressFill = document.querySelector('#distance-progress');

    if (!state.sitting) {
        // 沒人坐著，顯示未偵測狀態
        statusCircle.className = 'status-circle';
        statusLabel.textContent = '未偵測到使用者';
        metricValue.textContent = '--';
        progressFill.style.width = '0%';
        progressFill.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
    } else if (state.distance_safe) {
        // 有人坐著 且 距離安全
        statusCircle.className = 'status-circle safe';
        statusLabel.textContent = '安全距離';
        metricValue.textContent = '良好';
        progressFill.style.width = '100%';
        progressFill.style.background = 'linear-gradient(90deg, #10b981, #059669)';
    } else {
        // 有人坐著 但 距離過近
        statusCircle.className = 'status-circle danger';
        statusLabel.textContent = '距離過近';
        metricValue.textContent = '警告';
        progressFill.style.width = '40%';
        progressFill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
    }
}

function updateSittingCard() {
    const statusCircle = document.querySelector('#sitting-card .status-circle');
    const statusLabel = document.querySelector('#sitting-card .status-label');
    const timerValue = document.querySelector('#sitting-timer');
    const progressFill = document.querySelector('#sitting-progress');

    if (state.sitting) {
        const duration = state.sittingTotalDuration;
        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);

        timerValue.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

        // Calculate progress (based on 30-minute threshold)
        const progressPercent = Math.min((duration / CONFIG.SITTING_TRIGGER) * 100, 100);
        progressFill.style.width = `${progressPercent}%`;

        if (duration >= CONFIG.SITTING_TRIGGER) {
            statusCircle.className = 'status-circle warning';
            statusLabel.textContent = '建議休息';
            progressFill.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
        } else {
            statusCircle.className = 'status-circle safe';
            statusLabel.textContent = '正在監測';
            progressFill.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
        }
    } else {
        statusCircle.className = 'status-circle';
        statusLabel.textContent = '未偵測到';
        timerValue.textContent = '00:00';
        progressFill.style.width = '0%';
    }
}

function updateStatistics() {
    // Total monitoring time
    const totalMinutes = Math.floor(state.totalMonitoringTime / 60);
    document.querySelector('#total-time').textContent = `${totalMinutes} 分鐘`;

    // Safe distance percentage
    const safePercentage = state.totalChecks > 0
        ? Math.round((state.safeDistanceCount / state.totalChecks) * 100)
        : 100;
    document.querySelector('#safe-percentage').textContent = `${safePercentage}%`;

    // Alert count
    document.querySelector('#alert-count').textContent = state.alertCount;

    // Average sitting duration (simplified calculation)
    const avgSitting = state.sitting && state.sittingTotalDuration > 0
        ? Math.floor(state.sittingTotalDuration / 60000)
        : 0;
    document.querySelector('#avg-sitting').textContent = `${avgSitting} 分鐘`;
}

// =====================================
// Alert System
// =====================================

const activeAlerts = new Set();

function showAlert(type, title, message, alertId) {
    // Prevent duplicate alerts
    if (activeAlerts.has(alertId)) return;

    activeAlerts.add(alertId);
    state.alertCount++;

    const container = document.getElementById('alert-container');

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.dataset.alertId = alertId;

    const icon = type === 'danger' ? '⚠️' : '⏰';

    alert.innerHTML = `
        <div class="alert-content">
            <div class="alert-icon">${icon}</div>
            <div class="alert-message">
                <div class="alert-title">${title}</div>
                <div class="alert-description">${message}</div>
            </div>
        </div>
        <button class="alert-close" onclick="dismissAlert('${alertId}')">&times;</button>
    `;

    container.appendChild(alert);

    // Add to history
    addToHistory(type, title, message);

    // Auto-dismiss after 10 seconds
    setTimeout(() => {
        dismissAlert(alertId);
    }, 10000);
}

function dismissAlert(alertId) {
    const alert = document.querySelector(`[data-alert-id="${alertId}"]`);
    if (alert) {
        alert.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => {
            alert.remove();
            activeAlerts.delete(alertId);
        }, 300);
    }
}

function addToHistory(type, title, message) {
    const now = new Date();
    const timeString = now.toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    state.alertHistory.unshift({
        type,
        title,
        message,
        time: timeString,
        timestamp: now.getTime()
    });

    // Keep only latest items
    if (state.alertHistory.length > CONFIG.MAX_HISTORY_ITEMS) {
        state.alertHistory = state.alertHistory.slice(0, CONFIG.MAX_HISTORY_ITEMS);
    }

    renderHistory();
}

function renderHistory() {
    const container = document.getElementById('history-container');

    if (state.alertHistory.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                    <path d="M12 16v-4M12 8h.01"/>
                </svg>
                <p>目前沒有警示記錄</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.alertHistory.map(item => `
        <div class="history-item ${item.type}">
            <div class="history-time">${item.time}</div>
            <div class="history-message"><strong>${item.title}:</strong> ${item.message}</div>
        </div>
    `).join('');
}

// =====================================
// Chart
// =====================================

function initializeChart() {
    const ctx = document.getElementById('healthChart');

    healthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: state.chartData.labels,
            datasets: [
                {
                    label: '視距安全',
                    data: state.chartData.distanceData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    spanGaps: false  // 不連接斷點，null 值顯示為空白
                },
                {
                    label: '久坐狀態',
                    data: state.chartData.sittingData,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true,
                    spanGaps: false  // 不連接斷點
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#a0aec0',
                        font: {
                            family: "'Noto Sans TC', sans-serif"
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        color: '#718096',
                        callback: function (value) {
                            return value === 1 ? '是' : '否';
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#718096'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

function updateChartData() {
    const now = Date.now();

    // 只在間隔時間後才更新圖表（避免圖表點太密集）
    if (now - lastChartUpdateTime < CONFIG.CHART_UPDATE_INTERVAL) {
        return; // 還沒到更新時間，跳過
    }

    lastChartUpdateTime = now;

    const timeLabel = new Date(now).toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    state.chartData.labels.push(timeLabel);

    // 距離數據：只有在有人坐著時才記錄，否則記錄 null（圖表會顯示斷點）
    if (state.sitting) {
        state.chartData.distanceData.push(state.distance_safe ? 1 : 0);
    } else {
        state.chartData.distanceData.push(null); // 沒人坐著時，距離數據無意義
    }

    // 久坐數據：直接記錄 sitting 狀態
    state.chartData.sittingData.push(state.sitting ? 1 : 0);

    // Keep only recent data points (10 分鐘範圍)
    if (state.chartData.labels.length > CONFIG.MAX_CHART_POINTS) {
        state.chartData.labels.shift();
        state.chartData.distanceData.shift();
        state.chartData.sittingData.shift();
    }

    healthChart.update('none'); // Update without animation for performance
}

// =====================================
// Timer
// =====================================

function startTimer() {
    setInterval(() => {
        state.totalMonitoringTime++;
        updateStatistics();
    }, 1000);
}

// =====================================
// Error Handling
// =====================================

function showSystemError() {
    const statusBadge = document.getElementById('system-status');
    statusBadge.innerHTML = `
        <span class="status-dot" style="background: #ef4444;"></span>
        <span class="status-text" style="color: #ef4444;">連線異常</span>
    `;
}

// =====================================
// Utility Functions
// =====================================

// Make dismissAlert globally accessible
window.dismissAlert = dismissAlert;

console.log('✅ VisionWave Guardian 已就緒');
console.log('📊 使用模擬資料模式:', CONFIG.API_ENDPOINT === 'SIMULATED');
