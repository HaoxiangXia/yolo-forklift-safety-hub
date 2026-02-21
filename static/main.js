/**
 * 前端逻辑 - 升级版
 * 1. 顶部统计栏实时更新
 * 2. 运行时间前端每秒动态递增计算
 */

document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#device-table tbody');
    const wsStatus = document.querySelector('#ws-status');
    
    // 统计栏元素
    const statTotal = document.getElementById('stat-total');
    const statOnline = document.getElementById('stat-online');
    const statAlarm = document.getElementById('stat-alarm');

    let devicesData = []; // 存储最新的设备列表

    /**
     * 格式化运行时间为 HH:MM:SS
     * @param {string} bootTimeStr 启动时间字符串 (YYYY-MM-DD HH:MM:SS)
     * @param {number} onlineStatus 0或1
     * @returns {string}
     */
    function formatRuntime(bootTimeStr, onlineStatus) {
        if (onlineStatus === 0) return '<span class="status-offline">离线</span>';
        if (!bootTimeStr) return '00:00:00';

        // 将后端时间字符串转换为 Date 对象
        const bootDate = new Date(bootTimeStr.replace(/-/g, '/')); 
        const now = new Date();
        const diffSec = Math.floor((now - bootDate) / 1000);
        
        if (diffSec < 0) return '00:00:00';

        const h = Math.floor(diffSec / 3600).toString().padStart(2, '0');
        const m = Math.floor((diffSec % 3600) / 60).toString().padStart(2, '0');
        const s = (diffSec % 60).toString().padStart(2, '0');

        return `${h}:${m}:${s}`;
    }

    /**
     * 更新统计栏显示
     * @param {Object} stats 
     */
    function updateStatsBar(stats) {
        if (!stats) return;
        statTotal.textContent = stats.total || 0;
        statOnline.textContent = stats.online || 0;
        statAlarm.textContent = stats.alarm || 0;
    }

    /**
     * 渲染表格 DOM
     */
    function renderTable() {
        tableBody.innerHTML = '';
        
        devicesData.forEach(device => {
            const tr = document.createElement('tr');
            
            // 报警且在线时高亮
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
            tableBody.appendChild(tr);
        });
    }

    /**
     * 每秒更新一次运行时间显示，不请求后端
     */
    setInterval(() => {
        const cells = document.querySelectorAll('.runtime-cell');
        cells.forEach(cell => {
            const boot = cell.getAttribute('data-boot');
            const online = parseInt(cell.getAttribute('data-online'));
            cell.innerHTML = formatRuntime(boot, online);
        });
    }, 1000);

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

    // 接收后端推送
    socket.on('device_update', (data) => {
        console.log('Received real-time update:', data);
        // data 结构: { devices: [...], stats: { total, online, alarm } }
        devicesData = data.devices || [];
        updateStatsBar(data.stats);
        renderTable();
    });

    // 初始加载
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
