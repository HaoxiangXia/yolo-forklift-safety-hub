/**
 * 前端逻辑 - 柱状图趋势统计
 */

document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#device-table tbody');
    const wsStatusElement = document.querySelector('#ws-status');
    const statTotal = document.getElementById('stat-total');
    const statOnline = document.getElementById('stat-online');
    const statAlarm = document.getElementById('stat-alarm');

    const modal = document.getElementById('deviceModal');
    const closeBtn = document.querySelector('.close');
    const modalDeviceTitle = document.getElementById('modalDeviceTitle');
    const modalDeviceInfo = document.getElementById('modalDeviceInfo');
    const modalHistoryList = document.getElementById('modalHistoryList');

    let devicesData = [];
    let historyChart = null;
    let wsStatus = 'disconnected';

    const AUTH_TOKEN = window.APP_AUTH_TOKEN || '';

    function updateWsStatus(status, text) {
        wsStatus = status;
        wsStatusElement.textContent = `WebSocket: ${text}`;
        if (status === 'connected' || status === 'reconnected') {
            wsStatusElement.classList.add('ws-connected');
            wsStatusElement.classList.remove('ws-disconnected');
        } else {
            wsStatusElement.classList.add('ws-disconnected');
            wsStatusElement.classList.remove('ws-connected');
        }
    }

    function authHeaders() {
        const headers = {};
        if (AUTH_TOKEN) {
            headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
            headers['X-Auth-Token'] = AUTH_TOKEN;
        }
        return headers;
    }

    function formatRuntime(bootTimeStr, onlineStatus) {
        if (onlineStatus === 0) return '离线';
        if (!bootTimeStr) return '00:00:00';
        const bootDate = new Date(bootTimeStr.replace(/-/g, '/'));
        const now = new Date();
        const diffSec = Math.floor((now - bootDate) / 1000);
        if (diffSec < 0) return '00:00:00';
        const h = Math.floor(diffSec / 3600).toString().padStart(2, '0');
        const m = Math.floor((diffSec % 3600) / 60).toString().padStart(2, '0');
        const s = (diffSec % 60).toString().padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    function updateStatsBar(stats) {
        if (!stats) return;
        statTotal.textContent = stats.total || 0;
        statOnline.textContent = stats.online || 0;
        statAlarm.textContent = stats.alarm || 0;
    }

    function renderTable() {
        tableBody.innerHTML = '';
        devicesData.forEach(device => {
            const tr = document.createElement('tr');
            if (device.alarm_status === 1 && device.online_status === 1) {
                tr.className = 'alarm-active';
            }

            const tdDeviceId = document.createElement('td');
            // 使用 textContent 仅写入纯文本，可阻断外部数据被当作 HTML 执行，避免 XSS。
            tdDeviceId.textContent = device.device_id || '';

            const tdAlarm = document.createElement('td');
            tdAlarm.className = device.alarm_status === 1 ? 'alarm-active' : 'alarm-normal';
            tdAlarm.textContent = device.alarm_status === 1 ? '⚠️ 报警' : '正常';

            const tdErrorCount = document.createElement('td');
            tdErrorCount.textContent = String(device.error_count ?? 0);

            const tdRuntime = document.createElement('td');
            tdRuntime.className = 'runtime-cell';
            tdRuntime.dataset.boot = device.boot_time || '';
            tdRuntime.dataset.online = String(device.online_status ?? 0);
            tdRuntime.textContent = formatRuntime(device.boot_time, device.online_status);
            if (device.online_status === 0) {
                tdRuntime.classList.add('status-offline');
            }

            const tdUpdateTime = document.createElement('td');
            tdUpdateTime.className = 'update-time';
            tdUpdateTime.textContent = device.update_time || '';

            tr.appendChild(tdDeviceId);
            tr.appendChild(tdAlarm);
            tr.appendChild(tdErrorCount);
            tr.appendChild(tdRuntime);
            tr.appendChild(tdUpdateTime);

            tr.onclick = () => openDeviceModal(device);
            tableBody.appendChild(tr);
        });
    }

    async function openDeviceModal(device) {
        modalDeviceTitle.textContent = `设备报警趋势: ${device.device_id}`;
        modal.style.display = 'block';

        const onlineStatusText = device.online_status === 1 ? '在线' : '离线';
        modalDeviceInfo.innerHTML = '';
        const p = document.createElement('p');
        const strongStatus = document.createElement('strong');
        strongStatus.textContent = '当前状态:';
        p.appendChild(strongStatus);
        p.appendChild(document.createTextNode(` ${onlineStatusText} | `));

        const strongError = document.createElement('strong');
        strongError.textContent = '累计错误:';
        p.appendChild(strongError);
        p.appendChild(document.createTextNode(` ${device.error_count ?? 0}`));
        modalDeviceInfo.appendChild(p);

        try {
            const res = await fetch(`/device/${encodeURIComponent(device.device_id)}/history`, {
                headers: authHeaders()
            });
            const data = await res.json();

            renderHistoryList(data.raw_history || []);
            renderChart(data.labels, data.counts);
        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }

    function renderHistoryList(history) {
        modalHistoryList.innerHTML = '';
        history.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';

            const timeSpan = document.createElement('span');
            timeSpan.textContent = item.timestamp || '';

            const statusSpan = document.createElement('span');
            statusSpan.textContent = item.alarm === 1 ? '报警' : '正常';
            statusSpan.style.color = item.alarm === 1 ? 'red' : 'green';

            div.appendChild(timeSpan);
            div.appendChild(statusSpan);
            modalHistoryList.appendChild(div);
        });
    }

    function renderChart(labels, counts) {
        const ctx = document.getElementById('historyChart').getContext('2d');
        if (historyChart) {
            historyChart.destroy();
        }

        historyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '报警次数 (每分钟)',
                    data: counts,
                    backgroundColor: 'rgba(217, 83, 79, 0.6)',
                    borderColor: '#d9534f',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    closeBtn.onclick = () => {
        modal.style.display = 'none';
        if (historyChart) {
            historyChart.destroy();
            historyChart = null;
        }
    };

    window.onclick = (event) => {
        if (event.target === modal) closeBtn.onclick();
    };

    setInterval(() => {
        const cells = document.querySelectorAll('.runtime-cell');
        cells.forEach(cell => {
            const boot = cell.getAttribute('data-boot');
            const online = parseInt(cell.getAttribute('data-online'), 10);
            cell.textContent = formatRuntime(boot, online);
            cell.classList.toggle('status-offline', online === 0);
        });
    }, 1000);

    const socketOptions = AUTH_TOKEN ? { auth: { token: AUTH_TOKEN } } : {};
    const socket = io(socketOptions);

    // 统一维护连接状态，值班人员可从页面快速确认链路健康，避免误判系统“在线但无数据”。
    socket.on('connect', () => updateWsStatus('connected', '已连接'));
    socket.on('disconnect', () => updateWsStatus('disconnected', '已断开'));
    socket.on('reconnect_attempt', () => updateWsStatus('reconnect_attempt', '重连中'));
    socket.on('reconnect', () => updateWsStatus('reconnected', '已重连'));
    socket.on('connect_error', (err) => updateWsStatus('connect_error', `连接错误：${err?.message || '未知错误'}`));

    socket.on('device_update', (data) => {
        devicesData = data.devices || [];
        updateStatsBar(data.stats);
        renderTable();
    });

    async function init() {
        try {
            const res = await fetch('/api/latest', { headers: authHeaders() });
            const data = await res.json();
            devicesData = data.devices || [];
            updateStatsBar(data.stats);
            renderTable();
        } catch (e) {
            console.error('Init error:', e);
        }
    }
    init();
});
