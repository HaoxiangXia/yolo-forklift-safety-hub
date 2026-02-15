# 叉车作业人车互斥报警实时监控系统（YOLO Forklift Safety Hub）

一个基于 **Flask + MQTT + SQLite** 的轻量级监控 Demo，用于接收叉车安全相关事件，并在网页端实时展示设备状态与历史记录。

## 功能特性

- 订阅 MQTT 主题：`factory/forklift/+/alarm`
- 解析并存储设备上报数据到 SQLite
- 展示**每台设备最新状态**（报警/正常）
- 展示最近 50 条历史记录
- 前端每 3 秒自动轮询刷新
- 提供模拟数据发布脚本，便于本地联调

## 项目结构

```text
.
├── app.py                # Flask 入口，提供页面与 API
├── mqtt_client.py        # MQTT 订阅客户端，收到消息后写入数据库
├── db.py                 # SQLite 数据访问与表初始化
├── publish_test.py       # MQTT 模拟上报脚本
├── templates/
│   └── index.html        # 监控页面
├── static/
│   └── main.js           # 前端轮询与表格渲染
├── requirements.txt      # Python 依赖
└── alarm.db              # SQLite 数据库文件（运行后生成/更新）
```

## 运行环境

- Python 3.10+
- 可用的 MQTT Broker（默认配置为本机 `localhost:1883`）

> 推荐本地使用 Mosquitto 作为 Broker。

## 快速开始

### 1) 创建虚拟环境

```bash
python -m venv venv
```

### 2) 激活虚拟环境

Windows：

```powershell
venv\Scripts\activate
```

Linux/macOS：

```bash
source venv/bin/activate
```

### 3) 安装依赖

```bash
pip install -r requirements.txt
```

### 4) 启动 MQTT Broker

确保本机有可用 Broker，并监听：

- Host: `localhost`
- Port: `1883`

### 5) 启动 Web 服务（含 MQTT 订阅）

```bash
python app.py
```

启动后访问：

- 页面：http://127.0.0.1:5000/
- 最新状态 API：http://127.0.0.1:5000/api/latest
- 历史记录 API：http://127.0.0.1:5000/api/history

### 6) 启动模拟上报（可选）

```bash
python publish_test.py
```

该脚本会循环模拟两个设备（`FORK-001`、`FORK-002`）每 5 秒上报一次数据。

## MQTT 数据格式说明

### Topic 规则

```text
factory/forklift/{DEVICE_ID}/alarm
```

例如：

```text
factory/forklift/FORK-001/alarm
```

### Payload 示例（JSON）

```json
{
  "device_id": "FORK-001",
  "alarm": 1,
  "driver_present": 1,
  "outer_intrusion": 0,
  "timestamp": "2026-01-01 12:30:45"
}
```

字段说明：

- `device_id`：设备 ID（若主题可解析，服务端优先使用主题中的设备 ID）
- `alarm`：报警状态，`1`=报警，`0`=正常
- `driver_present`：驾驶员在位，`1`=在位，`0`=离开
- `outer_intrusion`：外部闯入，`1`=发现，`0`=无
- `timestamp`：上报时间（若缺失则由服务端补当前时间）

## 数据库说明

系统使用 SQLite，默认数据库文件：`alarm.db`。

表：`alarms`

- `id`：自增主键
- `device_id`：设备 ID
- `alarm`：报警状态
- `timestamp`：时间字符串
- `driver_present`：驾驶员在位状态
- `outer_intrusion`：外部闯入状态

## 常见问题

### 1) 页面没有数据

请依次检查：

1. MQTT Broker 是否启动并监听 `1883`
2. `app.py` 启动日志是否出现 MQTT 连接成功信息
3. 是否有设备或 `publish_test.py` 正在发布消息
4. 主题是否匹配 `factory/forklift/+/alarm`

### 2) Flask 启动后 MQTT 重复连接

`app.py` 已设置 `use_reloader=False` 来避免 Debug 模式下重复启动导致的双连接问题。

### 3) 如何切换 Broker 地址

修改 `mqtt_client.py` 与 `publish_test.py` 中的：

- `MQTT_BROKER`
- `MQTT_PORT`

## 后续可扩展方向

- 增加告警分级（高/中/低）
- 增加设备离线检测
- 支持 WebSocket 推送代替轮询
- 增加用户登录与权限管理
- 引入时序数据库与告警通知（短信/钉钉/企业微信）
