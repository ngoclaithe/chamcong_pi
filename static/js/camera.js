/**
 * Camera capture + per-image AJAX upload for user registration.
 *
 * Flow:
 *   1. User clicks "Bật Camera" → getUserMedia()
 *   2. User clicks "Chụp" or "Auto Chụp" → capture frame from <video>
 *   3. Each frame is converted to a Blob and uploaded via fetch to /users/upload_face
 *   4. Server validates face detection and saves to temp dir
 *   5. On form submit, only name + employee_code + session_id are sent
 */

const MAX_CAPTURES = 3;
let captures = [];         // Array of thumbnail dataURLs (small, for preview only)
let uploadedCount = 0;     // Number of successfully uploaded images
let stream = null;
let autoCapturing = false;

function getSessionId() {
    return document.getElementById('session_id').value;
}

async function startCamera() {
    const video = document.getElementById('cameraPreview');
    const btnStart = document.getElementById('btnStartCamera');
    const btnCapture = document.getElementById('btnCapture');
    const btnAutoCapture = document.getElementById('btnAutoCapture');

    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' }
        });
        video.srcObject = stream;
        btnStart.disabled = true;
        btnStart.textContent = '✅ Camera đã bật';
        btnCapture.disabled = false;
        btnAutoCapture.disabled = false;
    } catch (err) {
        alert('Không thể mở camera: ' + err.message);
    }
}

async function captureImage() {
    if (uploadedCount >= MAX_CAPTURES) return;

    const video = document.getElementById('cameraPreview');
    const canvas = document.getElementById('captureCanvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    // Mirror the capture to match the CSS scaleX(-1) on the video preview
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    // Show upload status
    showUploadStatus('Đang upload ảnh...');

    // Convert canvas to Blob (JPEG file)
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.90));

    // Upload via AJAX
    const formData = new FormData();
    formData.append('session_id', getSessionId());
    formData.append('image', blob, `face_${uploadedCount}.jpg`);

    try {
        const res = await fetch('/users/upload_face', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            // Save small thumbnail for UI preview
            const thumbUrl = canvas.toDataURL('image/jpeg', 0.4);
            captures.push(thumbUrl);
            uploadedCount = data.count;
            hideUploadStatus();
            updateCaptureUI();
        } else {
            hideUploadStatus();
            showUploadError(data.message || 'Upload thất bại');
        }
    } catch (err) {
        hideUploadStatus();
        showUploadError('Lỗi kết nối: ' + err.message);
        console.error('Upload error:', err);
    }
}

async function startAutoCapture() {
    if (autoCapturing) return;
    autoCapturing = true;

    const btnAutoCapture = document.getElementById('btnAutoCapture');
    btnAutoCapture.disabled = true;
    btnAutoCapture.textContent = '⏳ Đang chụp...';

    const remaining = MAX_CAPTURES - uploadedCount;

    for (let i = 0; i < remaining; i++) {
        if (!autoCapturing) break;
        await captureImage();
        // Wait 500ms between captures for different angles
        await new Promise(r => setTimeout(r, 500));
    }

    autoCapturing = false;
    btnAutoCapture.innerHTML = '<i data-lucide="zap"></i> Auto Chụp (15 ảnh)';
    btnAutoCapture.disabled = uploadedCount >= MAX_CAPTURES;
    lucide.createIcons();
}

function updateCaptureUI() {
    const grid = document.getElementById('captureGrid');
    const countSpan = document.getElementById('captureCount');
    const submitBtn = document.getElementById('btnSubmit');

    // Update count
    countSpan.textContent = `${uploadedCount}/${MAX_CAPTURES} ảnh`;

    // Update thumbnail grid
    grid.innerHTML = '';
    captures.forEach((thumbUrl, idx) => {
        const img = document.createElement('img');
        img.src = thumbUrl;
        img.className = 'capture-thumb filled';
        img.title = `Ảnh ${idx + 1} (click để xóa)`;
        img.onclick = () => removeCapture(idx);
        img.style.cursor = 'pointer';
        grid.appendChild(img);
    });

    // Enable submit if enough images
    submitBtn.disabled = uploadedCount < 1;

    // Disable capture buttons if max reached
    const btnCapture = document.getElementById('btnCapture');
    const btnAutoCapture = document.getElementById('btnAutoCapture');
    if (uploadedCount >= MAX_CAPTURES) {
        btnCapture.disabled = true;
        btnAutoCapture.disabled = true;
    }
}

async function removeCapture(idx) {
    try {
        const formData = new FormData();
        formData.append('session_id', getSessionId());
        formData.append('index', idx);

        const res = await fetch('/users/delete_face', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            captures.splice(idx, 1);
            uploadedCount = data.count;
            updateCaptureUI();
        }
    } catch (err) {
        console.error('Delete error:', err);
    }
}

function showUploadStatus(text) {
    const el = document.getElementById('uploadStatus');
    const textEl = document.getElementById('uploadStatusText');
    el.style.display = 'block';
    textEl.textContent = text;
}

function hideUploadStatus() {
    document.getElementById('uploadStatus').style.display = 'none';
}

function showUploadError(msg) {
    const el = document.getElementById('uploadStatus');
    const textEl = document.getElementById('uploadStatusText');
    el.style.display = 'block';
    textEl.textContent = '❌ ' + msg;
    textEl.style.color = 'var(--error)';
    setTimeout(() => {
        hideUploadStatus();
        textEl.style.color = '';
    }, 3000);
}

// Cleanup camera on page leave
window.addEventListener('beforeunload', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
});
