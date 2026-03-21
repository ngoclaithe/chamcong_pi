/**
 * Training progress polling.
 */

let pollingInterval = null;

async function startTraining() {
    const btnTrain = document.getElementById('btnTrain');
    btnTrain.disabled = true;
    btnTrain.textContent = '⏳ Đang khởi động...';

    try {
        const res = await fetch('/training/start', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            document.getElementById('trainingProgress').style.display = 'block';
            document.getElementById('trainingResult').style.display = 'none';
            startPolling();
        } else {
            alert(data.message);
            btnTrain.disabled = false;
            btnTrain.innerHTML = '<i data-lucide="rocket"></i> Bắt đầu Training';
            lucide.createIcons();
        }
    } catch (err) {
        alert('Lỗi: ' + err.message);
        btnTrain.disabled = false;
        btnTrain.innerHTML = '<i data-lucide="rocket"></i> Bắt đầu Training';
        lucide.createIcons();
    }
}

function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(pollStatus, 2000);
}

async function pollStatus() {
    try {
        const res = await fetch('/training/status');
        const data = await res.json();

        // Update progress bar
        document.getElementById('progressFill').style.width = data.progress + '%';
        document.getElementById('progressPercent').textContent = data.progress + '%';
        document.getElementById('progressText').textContent = data.message;

        // Update details
        if (data.epoch > 0) {
            document.getElementById('trainingDetails').innerHTML =
                `<p>Epoch: ${data.epoch}/${data.total_epochs} — Loss: ${data.loss}</p>`;
        }

        // Check if done
        if (!data.running) {
            clearInterval(pollingInterval);
            pollingInterval = null;

            const btnTrain = document.getElementById('btnTrain');
            btnTrain.disabled = false;
            btnTrain.innerHTML = '<i data-lucide="rocket"></i> Bắt đầu Training';

            // Show result
            const resultDiv = document.getElementById('trainingResult');
            const resultIcon = document.getElementById('resultIcon');
            const resultTitle = document.getElementById('resultTitle');
            const resultMessage = document.getElementById('resultMessage');

            resultDiv.style.display = 'block';

            if (data.error) {
                resultIcon.innerHTML = '<i data-lucide="x-circle" style="width:32px;height:32px;color:var(--error);"></i>';
                resultTitle.textContent = 'Training thất bại';
                resultMessage.textContent = data.message;
                resultDiv.style.borderColor = 'var(--error)';
            } else {
                resultIcon.innerHTML = '<i data-lucide="check-circle-2" style="width:32px;height:32px;color:var(--success);"></i>';
                resultTitle.textContent = 'Training hoàn tất!';
                resultMessage.textContent = data.message;
                resultDiv.style.borderColor = 'var(--success)';
            }

            lucide.createIcons();
        }
    } catch (err) {
        console.error('Poll error:', err);
    }
}

// Auto-start polling if training is already running
document.addEventListener('DOMContentLoaded', () => {
    const progressDiv = document.getElementById('trainingProgress');
    if (progressDiv && progressDiv.style.display !== 'none') {
        startPolling();
    }
});
