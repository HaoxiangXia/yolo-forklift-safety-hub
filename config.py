"""应用配置。"""

import os


def _get_bool(name, default=False):
    """从环境变量读取布尔值，保留该工具函数供后续可能的开关配置复用。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ==============================
# MQTT 连接配置
# ==============================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "factory/forklift/+/alarm"

# ==============================
# 数据库配置
# ==============================
DB_PATH = "alarm.db"
# SQLite 写锁冲突等待时长（毫秒）：给并发写入一点缓冲时间，减少瞬时锁冲突报错。
DB_BUSY_TIMEOUT_MS = 5000

# ==============================
# 鉴权配置
# ==============================
APP_ENV = "development"
AUTH_TOKEN = ""
# 开发阶段默认关闭，避免影响本地调试流程；生产启用时可直接改为 True 并配置 AUTH_TOKEN。
AUTH_ENABLED = False

# ==============================
# 设备离线检测配置
# ==============================
OFFLINE_CHECK_INTERVAL_SEC = 5
OFFLINE_TIMEOUT_SEC = 10

# ==============================
# 历史/趋势查询配置
# ==============================
HISTORY_LIMIT = 20
TREND_LIMIT = 20
