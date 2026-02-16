/**
 * 前端逻辑 - 升级版
 * 负责 WebSocket 连接、数据更新及运行时间实时刷新
 */

document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#device-table tbody');
    const wsStatus = document.querySelector('#ws-status');
    let devicesData = []; // 存储最新的设备列表

    /**
     * 计算运行时间字符串
     * @param {string} bootTimeStr 启动时间字符串
     * @param {number} onlineStatus 0或1
     * @returns {string}
     */
    function calculateUptime(bootTimeStr, onlineStatus) {
        if (onlineStatus === 0) return '<span class="status-offline">离线</span>';
        if (!bootTimeStr) return '-';

        const bootDate = new Date(bootTimeStr);
        const now = new Date();
        const diffMs = now - bootDate;
        
        if (diffMs < 0) return '0小时0分钟';

        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const hours = Math.floor(diffMinutes / 60);
        const minutes = diffMinutes % 60;

        return `${hours}小时${minutes}分钟`;
    }

    /**
     * 更新表格 DOM
     */
    function renderTable() {
        tableBody.innerHTML = '';
        
        devicesData.forEach(device => {
            const tr = document.createElement('tr');
            
            // 报警高亮显示
            if (device.alarm_status === 1 && device.online_status === 1) {
                tr.className = 'alarm-active';
            }

            const alarmText = device.alarm_status === 1 ? '⚠️ 报警' : '正常';
            const uptime = calculateUptime(device.boot_time, device.online_status);

            tr.innerHTML = `
                <td>${device.device_id}</td>
                <td class="${device.alarm_status === 1 ? 'alarm-active' : 'alarm-normal'}">${alarmText}</td>
                <td>${device.error_count}</td>
                <td>${uptime}</td>
                <td class="update-time">${device.update_time}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    /**
     * 定时刷新显示逻辑 (每分钟刷新一次运行时间)
     */
    setInterval(() => {
        if (devicesData.length > 0) {
            renderTable();
        }
    }, 60000);

    /**
     * 建立 WebSocket 连接
     */
    const socket = io();

    socket.on('connect', () => {
        console.log('WebSocket Connected');
        wsStatus.textContent = 'WebSocket: 已连接';
        wsStatus.className = 'ws-connected';
    });

    socket.on('disconnect', () => {
        console.log('WebSocket Disconnected');
        wsStatus.textContent = 'WebSocket: 已断开';
        wsStatus.className = 'ws-disconnected';
    });

    // 监听实时数据更新
    socket.on('device_update', (data) => {
        console.log('Received real-time update:', data);
        devicesData = data;
        renderTable();
    });

    // 初始加载
    async function init() {
        try {
            const res = await fetch('/api/latest');
            devicesData = await res.json();
            renderTable();
        } catch (e) {
            console.error('Init error:', e);
        }
    }

    init();
});
