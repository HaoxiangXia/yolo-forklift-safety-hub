# YOLO Forklift Safety Hub
## 叉车作业人车互斥报警系统云端部分

一个面向工业现场的实时安全监控系统，基于 **Flask + Socket.IO + MQTT + SQLite** 构建。

系统用于接收叉车设备上报数据，实时展示在线状态与报警状态，并提供离线检测、报警计数、防重复统计、历史记录与业务日志查询能力。

> **前端已重构为 Vue 3 SPA**（2026-04），采用 Glassmorphism（液态玻璃）+ Aurora Gradient（极光流动背景）UI 风格。

---

## ✨ 核心能力

- **实时状态看板**：后端通过 Socket.IO 推送 `device_update` / `position_update`，前端实时更新。
- **MQTT 报警接入**：订阅 `factory/forklift/+/alarm`，实时消费设备报警消息。
- **离线自动判定**：后台线程定时巡检，超时未上报自动标记离线并广播状态。
- **报警计数防重复**：仅在 `正常 -> 报警` 的状态跃迁时计数 +1。
- **运行时长统计**：在线期间持续统计；离线后停止累计，上线后可重新计算。
- **历史与趋势查询**：支持设备历史明细和报警趋势数据查询。
- **业务日志查询**：提供日志分页、级别筛选、设备ID筛选、分类筛选功能。
- **报警图片上传**：支持 MQTT+HTTP 混合方式批量上传报警图片。
- **设备位置追踪**：支持设备坐标存储与地图可视化展示。
- **可选鉴权**：支持 REST 与 Socket.IO token 校验（开发模式可关闭）。

---

## 🧱 技术栈

- **后端**：Flask、Flask-SocketIO、paho-mqtt
- **前端**：Vue 3 (Composition API)、Vue Router、Vite、ECharts、Axios、Socket.IO Client
- **数据库**：SQLite3
- **通信协议**：MQTT、WebSocket、REST API
- **UI 风格**：Glassmorphism（液态玻璃）+ Aurora Gradient（极光流动背景）

---

## 🏗️ 架构流程

```
MQTT Broker -> mqtt_client.py -> db.py (SQLite) -> SocketIO -> Vue SPA Frontend
                    |
                    v
              logger.py (dual write: file + SQLite)
```

---

## 📁 项目结构

```text
.
├── app.py                     # Flask + SocketIO 主程序（路由、离线检测、鉴权）
├── mqtt_client.py             # MQTT 订阅与消息处理
├── db.py                      # SQLite 读写（状态、计数、历史、趋势、位置）
├── logger.py                  # 统一日志记录（支持 ops/biz/sec 分类）
├── config.py                  # 系统配置（MQTT、离线阈值、鉴权、查询限制）
├── publish_test.py            # MQTT 设备模拟上报脚本
├── run_test.py                # 一键联调脚本（同时启动 app + publish）
├── vue-app/                   # Vue 3 前端项目
│   ├── src/
│   │   ├── views/
│   │   │   ├── Dashboard.vue  # 仪表盘（地图 + 报警趋势 + KPI）
│   │   │   ├── Devices.vue    # 设备列表（状态筛选 + 设备详情 + 图片查看）
│   │   │   └── Logs.vue       # 业务日志（分页 + 多条件筛选）
│   │   ├── components/
│   │   │   └── LineChart.vue  # ECharts 折线图可复用组件
│   │   ├── router/
│   │   │   └── index.js       # Vue Router 路由配置
│   │   ├── App.vue            # 根组件
│   │   └── main.js            # Vue 应用入口
│   └── dist/                  # 构建输出（生产环境部署）
├── static/
│   └── Dashboard.png          # 工厂地图背景图
├── images/
│   └── alarms/                # 报警图片存储目录
├── requirements.txt           # Python 依赖列表
├── AGENTS.md                  # 智能体开发指南
├── TODO.md                    # 功能规划与待实现项
└── README.md
```

---

## 🚀 快速开始

> **重要：始终使用 `venv` 虚拟环境运行 Python 命令！**

### 1. 准备 MQTT Broker
请先安装并启动 MQTT Broker（例如 Mosquitto）。

### 2. 安装依赖
```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. 构建前端（首次运行或修改前端后）
```bash
cd vue-app
npm install
npm run build
cd ..
```

### 4. 启动服务端
```bash
python app.py
```
默认访问地址：

- 监控页面：http://localhost:5000/
- 设备列表：http://localhost:5000/devices
- 日志查询：http://localhost:5000/logs

### 5. 启动模拟设备上报（可选）
```bash
python publish_test.py
```

### 6. 一键联调（可选）
```bash
python run_test.py
```

### 7. 前端开发模式（可选）
```bash
cd vue-app
npm run dev
```
开发服务器默认运行在 `http://localhost:5173`，自动代理 API 到 Flask 后端。

---

## 📡 MQTT 消息格式
系统默认处理如下 JSON：
```json
{
  "device_id": "FORK-001",
  "alarm": 1,
  "driver_present": 1,
  "outer_intrusion": 0,
  "timestamp": "2026-02-15 16:00:00"
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | string | 设备唯一标识 |
| alarm | int | 报警状态（0 正常 / 1 报警） |
| driver_present | int | 驾驶员在场（0/1） |
| outer_intrusion | int | 外部入侵检测（0/1） |
| timestamp | string | 设备上报时间 |
| image_urls | array | 报警图片 URL 列表（可选） |

---

## 🔌 主要接口

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/latest` | 返回全部设备最新状态与统计信息 |
| GET | `/api/logs` | 分页返回日志，支持 level/category/device_id 筛选 |
| GET | `/api/biz_logs` | 兼容旧接口（仅返回业务日志） |
| GET | `/api/device/<id>/history` | 设备历史明细与趋势数据 |
| GET | `/api/device/<id>/images` | 设备报警图片列表 |
| GET | `/api/device/<id>/latest-image` | 设备最新报警图片 |
| POST | `/api/upload-image` | 批量上传报警图片，返回图片 URL 列表 |
| GET | `/api/devices` | 获取所有设备位置和状态（Dashboard 用） |
| GET | `/api/recent-alarms` | 获取最近报警事件 |
| GET | `/images/<path>` | 图片访问服务 |
| GET | `/Dashboard.png` | 工厂地图背景图 |

### Socket.IO 事件

| 事件 | 方向 | 说明 |
|------|------|------|
| `device_update` | 服务端 → 客户端 | 设备状态更新广播 |
| `position_update` | 服务端 → 客户端 | 设备位置更新广播 |

### 鉴权

当 `AUTH_ENABLED = true` 时，REST API 需携带以下任一请求头：

- `Authorization: Bearer <token>`
- `X-Auth-Token: <token>`

Socket.IO 连接需在 auth  payload 或 query 参数中携带 `token`。

---

## 📴 离线判定规则

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 检测频率 | 5 秒 | 每 OFFLINE_CHECK_INTERVAL_SEC 秒检查一次 |
| 离线阈值 | 10 秒 | 超过 OFFLINE_TIMEOUT_SEC 秒未收到新数据 |
| 处理动作 | 标记离线 + 广播 | online_status 置为离线，通过 Socket.IO 广播 |

---

## ⚙️ 默认关键配置（config.py）

```python
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "factory/forklift/+/alarm"
OFFLINE_CHECK_INTERVAL_SEC = 5
OFFLINE_TIMEOUT_SEC = 10
AUTH_ENABLED = False
AUTH_TOKEN = ""
HISTORY_LIMIT = 20
TREND_LIMIT = 20
POSITION_UPDATE_INTERVAL_SEC = 5
MAX_IMAGE_SIZE_MB = 16
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
```

---

## 📌 适用场景

- 厂内叉车与行人混行区域的实时安全监控
- 设备在线状态与报警状态统一看板
- 报警记录留痕、趋势分析与运维排障
- 多设备位置追踪与地图可视化

---

## 📋 产品规划

详细的功能规划与待实现项请参考 [TODO.md](TODO.md)。
