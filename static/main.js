// 页面加载完成后立即刷新一次，然后每 3 秒刷新一次
document.addEventListener('DOMContentLoaded', () => {
    refreshData();
    setInterval(refreshData, 3000); // 3000 毫秒 = 3 秒
});

/**
 * 核心刷新函数
 */
async function refreshData() {
    console.log("正在刷新数据...");
    await updateLatestStatus();
    await updateHistory();
}

/**
 * 更新设备最新状态表格
 */
async function updateLatestStatus() {
    try {
        const response = await fetch('/api/latest');
        const data = await response.json();
        const listBody = document.getElementById('device-list');
        
        listBody.innerHTML = ''; // 清空当前表格

        data.forEach(item => {
            const row = document.createElement('tr');
            
            // 状态文字及样式
            const statusText = item.alarm === 1 ? '报警' : '正常';
            const statusClass = item.alarm === 1 ? 'status-alarm' : 'status-normal';
            
            // 辅助传感器状态
            const driverText = item.driver_present === 1 ? '在位' : '离开';
            const intrusionText = item.outer_intrusion === 1 ? '发现' : '无';

            row.innerHTML = `
                <td>${item.device_id}</td>
                <td class="${statusClass}">${statusText}</td>
                <td>${driverText}</td>
                <td>${intrusionText}</td>
                <td>${item.timestamp}</td>
            `;
            listBody.appendChild(row);
        });
    } catch (error) {
        console.error('获取最新状态失败:', error);
    }
}

/**
 * 更新历史数据表格
 */
async function updateHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        const listBody = document.getElementById('history-list');
        
        listBody.innerHTML = ''; // 清空

        data.forEach(item => {
            const row = document.createElement('tr');
            const statusText = item.alarm === 1 ? '报警' : '正常';
            const statusClass = item.alarm === 1 ? 'status-alarm' : 'status-normal';

            row.innerHTML = `
                <td>${item.device_id}</td>
                <td class="${statusClass}">${statusText}</td>
                <td>${item.timestamp}</td>
            `;
            listBody.appendChild(row);
        });
    } catch (error) {
        console.error('获取历史记录失败:', error);
    }
}
