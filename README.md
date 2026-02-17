# 叉车作业人车互斥报警系统 （YOLO Forklift Safety Hub）

这是一个基于 MQTT、Flask、SQLite 和 WebSocket 的实时设备监控与报警管理系统。

## 核心功能

1.  **实时状态监控**：通过 WebSocket 实现服务器主动推送，前端页面无需刷新即可实时更新。
2.  **人车互斥报警**：订阅 MQTT 报警主题，实时处理并显示叉车报警状态。
3.  **设备离线检测**：后端自动判定设备状态。若 10 秒内未收到数据，设备将被标记为“离线”。
4.  **智能错误计数**：
    *   仅在报警状态由“正常”变为“报警”时计数 +1。
    *   连续报警不重复计费，确保数据准确。
5.  **运行时间统计**：
    *   在线时动态显示“X小时Y分钟”。
    *   设备离线后重新上线，将重置启动时间 (Boot Time)。

## 技术栈

*   **后端**: Flask, Flask-SocketIO (WebSocket), paho-mqtt
*   **前端**: 原生 HTML5, JavaScript (ES6), Socket.IO Client
*   **数据库**: SQLite3
*   **通信协议**: MQTT, WebSocket, REST API

## 项目结构

```text
.
├── app.py                # Flask + SocketIO 主程序（包含离线检测线程）
├── mqtt_client.py        # MQTT 订阅模块（处理消息并触发 WebSocket 推送）
├── db.py                 # 数据库操作（包含错误计数与 BootTime 逻辑）
├── publish_test.py       # 模拟节点脚本（用于模拟正常、报警及离线场景）
├── templates/
│   └── index.html        # 监控页面模板
├── static/
│   └── main.js           # 前端 WebSocket 处理与 UI 渲染逻辑
└── requirements.txt      # 项目依赖
```

## 快速开始

### 1. 环境准备
确保已安装并运行 MQTT Broker（如 Mosquitto）。

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 运行服务端
```bash
python app.py
```
访问地址: `http://localhost:5000`

### 4. 运行模拟器
```bash
python publish_test.py
```

## 数据结构 (MQTT JSON)

```json
{
  "device_id": "FORK-001",
  "alarm": 1,
  "timestamp": "2026-02-15 16:00:00"
}
```

## 离线判定规则
*   **检测频率**: 每 5 秒检查一次。
*   **判定阈值**: 超过 10 秒未收到新数据。
*   **状态影响**: `online_status` 设为 0，前端显示“离线”，运行时间停止计算。
