// =====================================
// VisionWave API Controller
// =====================================

// State Management
const state = {
    distance_safe: true,  // true = 距離安全 (>= 60cm), false = 距離過近 (< 60cm)
    sitting: false        // true = 偵測到坐著, false = 未偵測到
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎮 VisionWave API 遙控器啟動');

    // Load saved state from localStorage
    loadState();

    // Set up event listeners
    setupEventListeners();

    // Update UI
    updateUI();

    // Save initial state
    saveState();
});

// Load state from localStorage
function loadState() {
    const savedState = localStorage.getItem('visionwave_api_state');
    if (savedState) {
        try {
            const parsed = JSON.parse(savedState);
            state.distance_safe = parsed.distance_safe;
            state.sitting = parsed.sitting;
            console.log('📥 已載入儲存的狀態:', state);
        } catch (error) {
            console.error('❌ 載入狀態失敗:', error);
        }
    }
}

// Save state to localStorage
function saveState() {
    const stateJson = JSON.stringify(state);
    localStorage.setItem('visionwave_api_state', stateJson);

    // Also save timestamp
    localStorage.setItem('visionwave_api_timestamp', Date.now().toString());

    console.log('💾 已儲存狀態:', state);
    updateUI();
}

// Setup event listeners
function setupEventListeners() {
    const distanceToggle = document.getElementById('distance-toggle');
    const sittingToggle = document.getElementById('sitting-toggle');

    distanceToggle.addEventListener('change', (e) => {
        state.distance_safe = e.target.checked;
        saveState();
        showNotification('distance_safe', e.target.checked);
    });

    sittingToggle.addEventListener('change', (e) => {
        state.sitting = e.target.checked;
        saveState();
        showNotification('sitting', e.target.checked);
    });
}

// Update UI
function updateUI() {
    // Update toggles
    document.getElementById('distance-toggle').checked = state.distance_safe;
    document.getElementById('sitting-toggle').checked = state.sitting;

    // Update labels
    const distanceLabel = document.getElementById('distance-label');
    const sittingLabel = document.getElementById('sitting-label');

    distanceLabel.textContent = state.distance_safe ? '安全 (true)' : '過近 (false)';
    distanceLabel.style.color = state.distance_safe ? '#10b981' : '#ef4444';

    sittingLabel.textContent = state.sitting ? '偵測到 (true)' : '未偵測 (false)';
    sittingLabel.style.color = state.sitting ? '#f472b6' : '#718096';

    // Update JSON display
    const jsonOutput = document.getElementById('json-output');
    jsonOutput.textContent = JSON.stringify(state, null, 2);
}

// Show notification (visual feedback)
function showNotification(field, value) {
    const messages = {
        'distance_safe_true': '✅ 設定為安全距離',
        'distance_safe_false': '⚠️ 設定為距離過近',
        'sitting_true': '🪑 設定為正在久坐',
        'sitting_false': '🚶 設定為未偵測到'
    };

    const key = `${field}_${value}`;
    console.log(messages[key]);
}

// Quick scenario presets
function setScenario(scenario) {
    switch (scenario) {
        case 'safe':
            // 理想狀態：安全距離，未久坐
            state.distance_safe = true;
            state.sitting = false;
            break;

        case 'distance-warning':
            // 距離警告：距離過近，未久坐
            state.distance_safe = false;
            state.sitting = false;
            break;

        case 'sitting':
            // 久坐：安全距離，正在久坐
            state.distance_safe = true;
            state.sitting = true;
            break;

        case 'danger':
            // 危險狀態：距離過近且久坐
            state.distance_safe = false;
            state.sitting = true;
            break;
    }

    saveState();

    // Visual feedback
    const btn = event.target.closest('.action-btn');
    if (btn) {
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            btn.style.transform = '';
        }, 150);
    }

    console.log(`🎬 場景設定: ${scenario}`, state);
}

// Make setScenario globally accessible
window.setScenario = setScenario;

// Test alert trigger
function triggerTestAlert() {
    // 設定測試標誌讓主頁面立即觸發久坐警示
    localStorage.setItem('visionwave_test_sitting_alert', Date.now().toString());

    // Visual feedback
    const btn = event.target.closest('.action-btn');
    if (btn) {
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            btn.style.transform = '';
        }, 150);
    }

    console.log('🧪 已觸發測試久坐警示');
}

// Make triggerTestAlert globally accessible
window.triggerTestAlert = triggerTestAlert;

// Monitor for changes from other tabs (if needed)
window.addEventListener('storage', (e) => {
    if (e.key === 'visionwave_api_state') {
        loadState();
        updateUI();
        console.log('🔄 從其他分頁同步狀態');
    }
});

console.log('✅ VisionWave API 遙控器準備就緒');
console.log('💡 開啟主監測頁面 (index.html) 進行測試');
