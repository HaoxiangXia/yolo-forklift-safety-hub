# YOLO Forklift Safety Hub
## 叉车作业人车互斥报警系统云端部分

一个面向工业现场的实时安全监控系统，基于 **Flask + Socket.IO + MQTT + SQLite** 构建。

系统用于接收叉车设备上报数据，实时展示在线状态与报警状态，并提供离线检测、报警计数、防重复统计、历史记录与业务日志查询能力。

---

## ✨ 核心能力

- **实时状态看板**：后端通过 Socket.IO 推送 `device_update`，前端无需刷新即可更新。
- **MQTT 报警接入**：订阅 `factory/forklift/+/alarm`，实时消费设备报警消息。
- **离线自动判定**：后台线程定时巡检，超时未上报自动标记离线并广播状态。
- **报警计数防重复**：仅在 `正常 -> 报警` 的状态跃迁时计数 +1。
- **运行时长统计**：在线期间持续统计；离线后停止累计，上线后可重新计算。
- **历史与趋势查询**：支持设备历史明细和报警趋势数据查询。
- **业务日志查询**：提供日志分页、级别筛选、设备ID筛选功能与独立日志页面。
- **可选鉴权**：支持 REST 与 Socket.IO token 校验（开发模式可关闭）。
- **图片上传**：支持 MQTT+HTTP 混合方式上传报警图片。

---

## 🧱 技术栈

- **后端**：Flask、Flask-SocketIO、paho-mqtt
- **前端**：HTML5、JavaScript（ES6）、Socket.IO Client
- **数据库**：SQLite3
- **通信协议**：MQTT、WebSocket、REST API

---

## 🏗️ 架构流程

```
MQTT Broker -> mqtt_client.py -> db.py (SQLite) -> SocketIO -> Frontend
                    |
                    v
              logger.py (dual write: file + SQLite)
```

---

## 📁 项目结构

```text
.
├── app.py                # Flask + SocketIO 主程序（路由、离线检测、鉴权）
├── mqtt_client.py        # MQTT 订阅与消息处理
├── db.py                 # SQLite 读写（状态、计数、历史、趋势）
├── logger.py             # 业务日志记录与分页查询
├── config.py             # 系统配置（MQTT、离线阈值、鉴权、查询限制）
├── publish_test.py       # MQTT 设备模拟上报脚本
├── run_test.py           # 一键联调脚本（同时启动 app + publish）
├── templates/
│   ├── index.html        # 实时监控页面
│   ├── dashboard.html    # 仪表盘页面
│   ├── devices.html      # 设备管理页面
│   └── logs.html         # 日志查询页面
├── static/
│   ├── main.js           # 前端渲染与 Socket.IO 交互逻辑
│   ├── echarts.min.js    # ECharts 图表库
│   ├── chart.js          # Chart.js 图表库
│   └── socket.io.min.js  # Socket.IO 客户端
├── images/
│   └── alarms/           # 报警图片存储目录
├── docs/
│   └── ui-design-guide.md      # UI 设计指南
├── requirements.txt      # Python 依赖列表
└── README.md
```

---

## 🚀 快速开始

1) 准备 MQTT Broker
请先安装并启动 MQTT Broker（例如 Mosquitto）。

2) 安装依赖
```bash
pip install -r requirements.txt
```
3) 启动服务端
```bash
python app.py
```
默认访问地址：

监控页面：http://localhost:5000/

日志页面：http://localhost:5000/logs

4) 启动模拟设备上报（可选）
```bash
python publish_test.py
```
5) 一键联调（可选）
```bash
python run_test.py
```
---

## 📡 MQTT 消息格式
系统默认处理如下 JSON：
```JSON
{
  "device_id": "FORK-001",
  "alarm": 1,
  "timestamp": "2026-02-15 16:00:00"
}
```
字段说明：

device_id：设备唯一标识

alarm：报警状态（1 表示报警）

timestamp：设备上报时间

---

## 🔌 主要接口
GET /api/latest：返回全部设备最新状态与统计信息。

GET /api/biz_logs?page=1&page_size=20：分页返回业务日志，支持以下筛选参数：
- `level`：日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- `device_id`：设备ID筛选

GET /api/device/<device_id>/history：返回设备历史明细与趋势数据。

POST /api/upload-image：上传报警图片，返回图片 URL。

当鉴权开启时，REST API 需携带以下任一请求头：

Authorization: Bearer <token>

X-Auth-Token: <token>

---

## 📴 离线判定规则
检测频率：每 OFFLINE_CHECK_INTERVAL_SEC 秒检查一次（默认 5 秒）

离线阈值：超过 OFFLINE_TIMEOUT_SEC 秒未收到新数据（默认 10 秒）

处理动作：设备 online_status 置为离线，并通过 Socket.IO 广播更新

---

## ⚙️ 默认关键配置（config.py）
MQTT_BROKER = "localhost"

MQTT_PORT = 1883

MQTT_TOPIC = "factory/forklift/+/alarm"

OFFLINE_CHECK_INTERVAL_SEC = 5

OFFLINE_TIMEOUT_SEC = 10

AUTH_ENABLED = False

AUTH_TOKEN = ""

HISTORY_LIMIT = 20

TREND_LIMIT = 20

---

## 📌 适用场景
厂内叉车与行人混行区域的实时安全监控

设备在线状态与报警状态统一看板

报警记录留痕、趋势分析与运维排障
