/**
 * 前端逻辑 - 柱状图趋势统计
 */

document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#device-table tbody');
    const wsStatus = document.querySelector('#ws-status');
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

    function formatRuntime(bootTimeStr, onlineStatus) {
        if (onlineStatus === 0) return '<span class="status-offline">离线</span>';
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
            const alarmText = device.alarm_status === 1 ? '⚠️ 报警' : '正常';
            const runtime = formatRuntime(device.boot_time, device.online_status);

            tr.innerHTML = `
                <td>${device.device_id}</td>
                <td class="${device.alarm_status === 1 ? 'alarm-active' : 'alarm-normal'}">${alarmText}</td>
                <td>${device.error_count}</td>
                <td class="runtime-cell" data-boot="${device.boot_time}" data-online="${device.online_status}">
                    ${runtime}
                </td>
                <td class="update-time">${device.update_time}</td>
            `;
            tr.onclick = () => openDeviceModal(device);
            tableBody.appendChild(tr);
        });
    }

    async function openDeviceModal(device) {
        modalDeviceTitle.textContent = `设备报警趋势: ${device.device_id}`;
        modal.style.display = 'block';
        
        const onlineStatusText = device.online_status === 1 ? '在线' : '离线';
        modalDeviceInfo.innerHTML = `
            <p><strong>当前状态:</strong> ${onlineStatusText} | 
               <strong>累计错误:</strong> ${device.error_count}</p>
        `;

        try {
            const res = await fetch(`/device/${device.device_id}/history`);
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
            const statusText = item.alarm === 1 ? '<span style="color:red">报警</span>' : '<span style="color:green">正常</span>';
            div.innerHTML = `<span>${item.timestamp}</span><span>${statusText}</span>`;
            modalHistoryList.appendChild(div);
        });
    }

    function renderChart(labels, counts) {
        const ctx = document.getElementById('historyChart').getContext('2d');
        if (historyChart) {
            historyChart.destroy();
        }

        historyChart = new Chart(ctx, {
            type: 'bar', // 改为柱状图
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
        if (event.target == modal) closeBtn.onclick();
    };

    setInterval(() => {
        const cells = document.querySelectorAll('.runtime-cell');
        cells.forEach(cell => {
            const boot = cell.getAttribute('data-boot');
            const online = parseInt(cell.getAttribute('data-online'));
            cell.innerHTML = formatRuntime(boot, online);
        });
    }, 1000);

    const socket = io();
    socket.on('device_update', (data) => {
        devicesData = data.devices || [];
        updateStatsBar(data.stats);
        renderTable();
    });

    async function init() {
        try {
            const res = await fetch('/api/latest');
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
