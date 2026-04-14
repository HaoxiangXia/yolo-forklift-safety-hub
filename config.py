"""应用配置。"""

import os

def _get_bool(name, default=False):
    """从环境变量读取布尔值，保留该工具函数供后续可能的开关配置复用。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _get_int(name, default=0):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default

def _get_str(name, default=""):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()

# ==============================
# MQTT 连接配置
# ==============================
MQTT_BROKER = _get_str("MQTT_BROKER", "localhost")
MQTT_PORT = _get_int("MQTT_PORT", 1883)
MQTT_TOPIC = _get_str("MQTT_TOPIC", "factory/forklift/+/alarm")
# 开发环境默认允许 MQTT 不可用时继续启动 Web，便于纯前端/接口联调。
MQTT_REQUIRED = _get_bool("MQTT_REQUIRED", False)

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
OFFLINE_CHECK_INTERVAL_SEC = _get_int("OFFLINE_CHECK_INTERVAL_SEC", 5)
OFFLINE_TIMEOUT_SEC = _get_int("OFFLINE_TIMEOUT_SEC", 10)

# ==============================
# 历史/趋势查询配置
# ==============================
HISTORY_LIMIT = 20
TREND_LIMIT = 20

# ==============================
# 设备位置模拟配置（仅用于测试）
# ==============================
POSITION_UPDATE_INTERVAL_SEC = _get_int("POSITION_UPDATE_INTERVAL_SEC", 5)
POSITION_MOVE_RANGE = _get_int("POSITION_MOVE_RANGE", 20)

# ==============================
# 图片上传配置
# ==============================
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_IMAGE_SIZE_MB = 16

# ==============================
# LLM 多模态描述配置
# ==============================
OPENAI_API_KEY = _get_str("OPENAI_API_KEY", "")
OPENAI_BASE_URL = _get_str("OPENAI_BASE_URL", "")
LLM_ENABLED = _get_bool("LLM_ENABLED", bool(OPENAI_API_KEY))
LLM_PROVIDER = _get_str("LLM_PROVIDER", "openai")
LLM_MODEL = _get_str("LLM_MODEL", "gpt-4.1-mini")
LLM_TIMEOUT_SEC = _get_int("LLM_TIMEOUT_SEC", 20)
LLM_MAX_RETRIES = _get_int("LLM_MAX_RETRIES", 2)
LLM_POLL_INTERVAL_SEC = _get_int("LLM_POLL_INTERVAL_SEC", 5)
LLM_RETRY_INTERVAL_SEC = _get_int("LLM_RETRY_INTERVAL_SEC", 60)
