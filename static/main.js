/**
 * 前端实时更新逻辑
 * 使用 Socket.IO 与后端建立长连接
 */

document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#device-table tbody');
    const wsStatus = document.querySelector('#ws-status');

    /**
     * 更新表格内容
     * @param {Array} devices 设备列表数据
     */
    function updateTable(devices) {
        tableBody.innerHTML = ''; // 清空当前表格
        
        devices.forEach(device => {
            const tr = document.createElement('tr');
            
            // 如果有报警且在线，整行高亮显示
            if (device.alarm === 1 && device.online_status === 1) {
                tr.className = 'alarm-active';
            }

            // 格式化数据
            const alarmText = device.alarm === 1 ? '⚠️ 报警' : '正常';
            const onlineText = device.online_status === 1 ? '● 在线' : '○ 离线';
            const onlineClass = device.online_status === 1 ? 'status-online' : 'status-offline';
            const driverText = device.driver_present === 1 ? '在位' : '空置';
            const intrusionText = device.outer_intrusion === 1 ? '有侵入' : '无';

            tr.innerHTML = `
                <td>${device.device_id}</td>
                <td class="${device.alarm === 1 ? 'alarm-active' : 'alarm-normal'}">${alarmText}</td>
                <td class="${onlineClass}">${onlineText}</td>
                <td>${driverText}</td>
                <td>${intrusionText}</td>
                <td class="update-time">${device.last_timestamp || device.last_seen}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    /**
     * 初始加载数据
     */
    async function loadInitialData() {
        try {
            const response = await fetch('/api/latest');
            const data = await response.json();
            updateTable(data);
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    // 1. 建立 WebSocket 连接
    const socket = io();

    // 2. 连接成功回调
    socket.on('connect', () => {
        console.log('Connected to server via WebSocket');
        wsStatus.textContent = 'WebSocket: 已连接';
        wsStatus.className = 'ws-connected';
        // 连接后刷新一次数据，确保同步
        loadInitialData();
    });

    // 3. 连接断开回调
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        wsStatus.textContent = 'WebSocket: 已断开';
        wsStatus.className = 'ws-disconnected';
    });

    // 4. 监听后端推送的 'device_update' 事件
    socket.on('device_update', (data) => {
        console.log('Received real-time update:', data);
        updateTable(data);
    });

    // 初始加载一次数据
    loadInitialData();
});
