/**
 * 前端综合逻辑：包含实时状态更新、带 Token 的双通道鉴权(WebSocket + API)、图表弹窗。
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM 元素引用
    const tableBody = document.querySelector('#device-table tbody');
    const wsStatusElement = document.querySelector('#ws-status');
    
    // 顶部统计数字
    const statTotal = document.getElementById('stat-total');
    const statOnline = document.getElementById('stat-online');
    const statAlarm = document.getElementById('stat-alarm');

    // 弹窗相关
    const modal = document.getElementById('deviceModal');
    const closeBtn = document.querySelector('.close');
    const modalDeviceTitle = document.getElementById('modalDeviceTitle');
    const modalDeviceInfo = document.getElementById('modalDeviceInfo');
    const modalHistoryList = document.getElementById('modalHistoryList');

    // 数据缓存
    let deviceData = {}; 
    let historyChart = null;
    let wsStatus = 'disconnected';
    const OFFLINE_THRESHOLD = 10 * 1000;
    const AUTH_TOKEN = window.APP_AUTH_TOKEN || '';

    // ===================================
    // 鉴权配置助手
    // ===================================
    function authHeaders() {
        const headers = {};
        if (AUTH_TOKEN) {
            headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
            headers['X-Auth-Token'] = AUTH_TOKEN;
        }
        return headers;
    }

    // ===================================
    // Socket.io 初始化
    // ===================================
    const socket = io({
        auth: { token: AUTH_TOKEN }
    });

    socket.on("connect", () => {
        wsStatusElement.className = 'ws-connected';
        wsStatusElement.textContent = 'Socket.io: 已连接';
    });

    socket.on("disconnect", () => {
        wsStatusElement.className = 'ws-disconnected';
        wsStatusElement.textContent = 'Socket.io: 已断开';
    });

    socket.on("connect_error", (err) => {
        console.error("Socket.io 连接错误:", err);
        wsStatusElement.className = 'ws-disconnected';
        wsStatusElement.textContent = `Socket.io: 拒绝连接 (${err.message})`;
    });

    socket.on("device_update", (data) => {
        // 更新总体设备数据
        if (data.devices && Array.isArray(data.devices)) {
            data.devices.forEach(device => updateDeviceCache(device));
            renderDevices();
            updateStats({
                total: data.stats?.total || 0,
                online: data.stats?.online || 0,
                alarm: data.stats?.alarm || 0
            });
        }
    });

    // ===================================
    // 初始化数据流
    // ===================================
    async function fetchInitialData() {
        try {
            const devRes = await fetch("/api/latest", { headers: authHeaders() });
            if (!devRes.ok) throw new Error("API 响应错误: " + devRes.statusText);
            const devData = await devRes.json();
            
            if (devData.devices && Array.isArray(devData.devices)) {
                devData.devices.forEach(device => updateDeviceCache(device));
                renderDevices();
                updateStats(devData.stats);
            }
        } catch (e) {
            console.error("获取初始数据失败:", e);
        }
    }

    // ===================================
    // 渲染机制与更新
    // ===================================
    function updateDeviceCache(device) {
        const deviceId = device.device_id || device.id;
        if (!deviceId) return;
        
        deviceData[deviceId] = {
            ...deviceData[deviceId],
            ...device
        };
    }

    function updateStats(stats) {
        if (!stats) return;
        statTotal.textContent = stats.total || 0;
        statOnline.textContent = stats.online || 0;
        statAlarm.textContent = stats.alarm || 0;
    }
    
    function formatToChinaTime(utcString) {
    if (!utcString) return '-';

    const date = new Date(utcString);
    if (isNaN(date)) return utcString;

    return date.toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai",
        hour12: false
    });
    }
   
    function formatRuntime(bootTimeStr, onlineStatus) {
        if (onlineStatus === 0) return '——';
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

    function renderDevices() {
        tableBody.innerHTML = '';
        Object.values(deviceData).forEach(device => {
            const tr = document.createElement('tr');
            if (device.alarm_status === 1 && device.online_status === 1) {
                tr.className = 'alarm-active';
            }

            const tdId = document.createElement('td');
            tdId.textContent = device.device_id || '';
            
            const tdOnline = document.createElement('td');
            tdOnline.textContent = device.online_status === 1 ? '在线' : '离线';
            tdOnline.className = device.online_status === 1 ? 'status-online' : 'status-offline';

            const tdAlarm = document.createElement('td');
            tdAlarm.textContent = device.alarm_status === 1 ? '⚠️ 报警' : '正常';
            if (device.alarm_status === 1) tdAlarm.style.color = 'red';
            
            const tdError = document.createElement('td');
            tdError.textContent = device.error_count || '0';

            const tdRuntime = document.createElement('td');
            tdRuntime.textContent = formatRuntime(device.boot_time, device.online_status);

            const tdUpdate = document.createElement('td');
            tdUpdate.textContent = formatToChinaTime(device.last_seen || device.update_time);
            tdUpdate.className = 'update-time';

            const tdImage = document.createElement('td');
            const imgBtn = document.createElement('button');
            imgBtn.textContent = '查看图片';
            imgBtn.style.padding = '4px 8px';
            imgBtn.style.fontSize = '0.85em';
            imgBtn.style.cursor = 'pointer';
            imgBtn.onclick = (e) => {
                e.stopPropagation();
                openImageModal(device.device_id);
            };
            tdImage.appendChild(imgBtn);

            tr.appendChild(tdId);
            tr.appendChild(tdOnline);
            tr.appendChild(tdAlarm);
            tr.appendChild(tdError);
            tr.appendChild(tdRuntime);
            tr.appendChild(tdUpdate);
            tr.appendChild(tdImage);

            // 点击行，触发图表展示
            tr.addEventListener('click', () => {
                openDeviceModal(device);
            });

            tableBody.appendChild(tr);
        });
    }

    // 每秒刷新运行时间
    setInterval(() => {
        renderDevices();
    }, 1000);

    // ===================================
    // 弹窗与图表逻辑
    // ===================================
    async function openDeviceModal(device) {
        modal.style.display = 'block';
        modalDeviceTitle.textContent = `设备详情: ${device.device_id}`;
        
        const runtime = formatRuntime(device.boot_time, device.online_status);
        modalDeviceInfo.innerHTML = `
            <p><strong>状态:</strong> ${device.online_status === 1 ? '在线' : '离线'} | <strong>当前报警:</strong> ${device.alarm_status === 1 ? '是' : '否'}</p>
            <p><strong>错误次数:</strong> ${device.error_count}</p>
            <p><strong>运行时间:</strong> ${runtime}</p>
        `;

        try {
            const res = await fetch(`/api/device/${device.device_id}/history`, { headers: authHeaders() });
            if (!res.ok) throw new Error("获取历史记录失败");
            const data = await res.json();
            
            renderChart(data.labels, data.counts);
            renderHistoryList(data.history);
        } catch (err) {
            console.error(err);
            modalHistoryList.innerHTML = `<p style="color:red">无法获取历史记录或暂无数据</p>`;
        }
    }

    function renderChart(labels, counts) {
        if (!labels || !counts) return;

        const ctx = document.getElementById('historyChart').getContext('2d');
        if (historyChart) {
            historyChart.destroy();
        }

        historyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '报警次数 (次/分钟)',
                    data: counts,
                    backgroundColor: 'rgba(217, 83, 79, 0.6)',
                    borderColor: 'rgba(217, 83, 79, 1)',
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

    function renderHistoryList(historyData) {
        modalHistoryList.innerHTML = '';
        if (!historyData || historyData.length === 0) {
            modalHistoryList.innerHTML = '<p>暂无记录</p>';
            return;
        }

        historyData.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            const statusText = item.alarm === 1 ? '<span style="color:red;font-weight:bold;">报警</span>' : '<span style="color:green;">正常</span>';
            div.innerHTML = `<span>状态: ${statusText}</span> <span style="color:#666;font-size:0.9em;">上报时间: ${formatToChinaTime(item.timestamp)}</span>`;
            modalHistoryList.appendChild(div);
        });
    }

    // 关闭弹窗
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    }
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    // ===================================
    // 报警图片弹窗逻辑
    // ===================================
    const imageModal = document.getElementById('imageModal');
    const imageModalClose = document.getElementById('imageModalClose');
    const imageModalTitle = document.getElementById('imageModalTitle');
    const imageList = document.getElementById('imageList');

    imageModalClose.onclick = function() {
        imageModal.style.display = 'none';
    };
    window.onclick = function(event) {
        if (event.target == imageModal) {
            imageModal.style.display = 'none';
        }
    };

    async function openImageModal(deviceId) {
        imageModal.style.display = 'block';
        imageModalTitle.textContent = `报警图片 - ${deviceId}`;
        imageList.innerHTML = '<p>加载中...</p>';

        try {
            const res = await fetch(`/api/device/${deviceId}/images`, { headers: authHeaders() });
            if (!res.ok) throw new Error("获取图片列表失败");
            const data = await res.json();

            imageList.innerHTML = '';
            if (!data.images || data.images.length === 0) {
                imageList.innerHTML = '<p>暂无报警图片</p>';
                return;
            }

            data.images.forEach(img => {
                const imgContainer = document.createElement('div');
                imgContainer.style.textAlign = 'center';
                
                const imgElement = document.createElement('img');
                imgElement.src = `/${img.image_path}`;
                imgElement.style.maxWidth = '300px';
                imgElement.style.maxHeight = '300px';
                imgElement.style.border = '1px solid #ddd';
                imgElement.style.borderRadius = '4px';
                
                const imgTime = document.createElement('p');
                imgTime.textContent = img.timestamp;
                imgTime.style.fontSize = '0.85em';
                imgTime.style.color = '#666';
                
                imgContainer.appendChild(imgElement);
                imgContainer.appendChild(imgTime);
                imageList.appendChild(imgContainer);
            });
        } catch (err) {
            console.error(err);
            imageList.innerHTML = `<p style="color:red">加载图片失败: ${err.message}</p>`;
        }
    }

    // 页面关闭时断开连接
    window.onbeforeunload = function() {
        socket.disconnect();
    };

    // 启动数据流
    fetchInitialData();
});
