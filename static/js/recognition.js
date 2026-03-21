/**
 * Live recognition — auto-start, shows face crop in results.
 *
 * Features:
 *   - Auto-starts on page load (no button needed)
 *   - Polls /recognition/detect every 500ms
 *   - Shows cropped face image + name + confidence in results panel
 *   - Updates attendance list in real-time
 *   - 5s cooldown after successful recognition
 */

let cooldownActive = false;
let cooldownSeconds = 0;
let cooldownInterval = null;

// Auto-start recognition on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchTodayAttendance();
    recognitionLoop();
});

async function recognitionLoop() {
    if (cooldownActive) return;

    try {
        const res = await fetch('/recognition/detect', { method: 'POST' });
        const data = await res.json();

        if (data.success && data.results.length > 0) {
            const recognized = data.results.filter(r => r.user_id !== null);
            const unknown = data.results.filter(r => r.user_id === null);

            if (recognized.length > 0) {
                showRecognizedResult(recognized[0]);

                if (recognized.some(r => r.logged)) {
                    fetchTodayAttendance();
                }

                startCooldown();
                return;
            }

            if (unknown.length > 0) {
                showUnknownFace(unknown[0]);
            }
        } else {
            showScanningState();
        }
    } catch (err) {
        console.error('Recognition error:', err);
    }

    if (!cooldownActive) {
        setTimeout(recognitionLoop, 500);
    }
}

function showRecognizedResult(result) {
    const container = document.getElementById('recognitionResults');
    const confPercent = (result.confidence * 100).toFixed(0);
    const confClass = result.confidence >= 0.8 ? 'badge-success'
                    : result.confidence >= 0.6 ? 'badge-info' : 'badge-warning';

    const faceImg = result.face_b64
        ? `<img src="data:image/jpeg;base64,${result.face_b64}"
               style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover;
                      border: 3px solid var(--accent); margin: 0 auto 10px; display: block;">`
        : `<div style="
                width: 80px; height: 80px;
                background: linear-gradient(135deg, var(--accent), #06b6d4);
                border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                font-size: 32px; font-weight: 700; color: white;
                margin: 0 auto 10px;
            ">${result.name ? result.name.charAt(0).toUpperCase() : '?'}</div>`;

    container.innerHTML = `
        <div style="
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(6, 182, 212, 0.08));
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            animation: fadeInScale 0.3s ease;
        ">
            ${faceImg}
            <div style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                ${result.name}
            </div>
            ${result.employee_code
                ? `<div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 10px;">${result.employee_code}</div>`
                : ''}
            <span class="badge ${confClass}" style="font-size: 13px; padding: 3px 10px;">
                ${confPercent}% match
            </span>
            ${result.logged
                ? `<div style="margin-top: 8px; color: var(--success); font-size: 13px; font-weight: 500;">
                       ✓ Đã chấm công
                   </div>`
                : `<div style="margin-top: 8px; color: var(--text-muted); font-size: 12px;">
                       Đã chấm công trước đó
                   </div>`
            }
        </div>
    `;

    const badge = document.getElementById('statusBadge');
    badge.textContent = '✓ Nhận diện';
    badge.className = 'badge badge-success';
}

function showUnknownFace(result) {
    const container = document.getElementById('recognitionResults');
    const confPercent = (result.confidence * 100).toFixed(0);

    const faceImg = result.face_b64
        ? `<img src="data:image/jpeg;base64,${result.face_b64}"
               style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover;
                      border: 2px solid var(--warning); margin: 0 auto 8px; display: block;">`
        : '';

    container.innerHTML = `
        <div style="
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        ">
            ${faceImg}
            <div style="font-size: 14px; color: var(--warning); font-weight: 600; margin-bottom: 4px;">
                ⚠ Không nhận diện được
            </div>
            <div style="font-size: 12px; color: var(--text-muted);">
                Confidence: ${confPercent}% (dưới ngưỡng)
            </div>
        </div>
    `;
}

function showScanningState() {
    const container = document.getElementById('recognitionResults');
    container.innerHTML = `
        <div class="empty-state" style="padding: 24px;">
            <div class="empty-state-icon"><i data-lucide="scan-face"></i></div>
            <div class="empty-state-text" style="font-size: 14px;">Đang quét...</div>
            <div class="empty-state-sub" style="font-size: 12px;">Đặt khuôn mặt vào khung xanh trên camera</div>
        </div>
    `;
    lucide.createIcons();
}

function startCooldown() {
    cooldownActive = true;
    cooldownSeconds = 5;

    const cooldownCard = document.getElementById('cooldownCard');
    const cooldownTimer = document.getElementById('cooldownTimer');
    cooldownCard.style.display = 'block';
    cooldownTimer.textContent = cooldownSeconds;

    cooldownInterval = setInterval(() => {
        cooldownSeconds--;
        cooldownTimer.textContent = cooldownSeconds;

        if (cooldownSeconds <= 0) {
            clearCooldown();
            showScanningState();
            const badge = document.getElementById('statusBadge');
            badge.textContent = 'Đang quét...';
            badge.className = 'badge badge-success';
            recognitionLoop();
        }
    }, 1000);
}

function clearCooldown() {
    cooldownActive = false;
    cooldownSeconds = 0;
    if (cooldownInterval) {
        clearInterval(cooldownInterval);
        cooldownInterval = null;
    }
    const cooldownCard = document.getElementById('cooldownCard');
    if (cooldownCard) cooldownCard.style.display = 'none';
}

// ===== Today's Attendance =====

async function fetchTodayAttendance() {
    try {
        const res = await fetch('/recognition/today');
        const data = await res.json();
        if (data.success) {
            renderAttendanceList(data.records);
        }
    } catch (err) {
        console.error('Fetch attendance error:', err);
    }
}

function renderAttendanceList(records) {
    const container = document.getElementById('todayLog');

    if (!records || records.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">Chưa có dữ liệu hôm nay</p>';
        return;
    }

    let html = '';
    records.forEach(r => {
        const initial = r.user_name ? r.user_name.charAt(0).toUpperCase() : '?';
        const time = r.timestamp ? new Date(r.timestamp).toLocaleTimeString('vi-VN') : '--:--';
        const conf = r.confidence ? `${(r.confidence * 100).toFixed(0)}%` : '';

        html += `
            <div class="result-card" style="animation: slideIn 0.2s ease;">
                <div class="result-avatar">${initial}</div>
                <div class="result-info">
                    <div class="result-name">${r.user_name}</div>
                    <div class="result-code">${r.employee_code || ''}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">${time}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">${conf}</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}
