import logging
import json
import os
import sqlite3
from datetime import datetime

# 从根目录配置导入DB_PATH
try:
    from config import DB_PATH
except ImportError:
    # 兼容单独运行此脚本的情况
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import DB_PATH

# =========================
# 日志存储配置
# =========================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "ops.log")

# =========================
# logger 对象
# =========================
logger = logging.getLogger("forklift")
logger.setLevel(logging.DEBUG)  # DEBUG 级别可在开发时打开
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# =========================
# Biz 日志入库
# =========================
def save_biz_log(ts, level, event, device_id, message, extra=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS biz_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            event TEXT,
            device_id TEXT,
            message TEXT,
            extra TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO biz_logs (ts, level, event, device_id, message, extra)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ts, level, event, device_id, message, json.dumps(extra, ensure_ascii=False) if extra else None))
    conn.commit()
    conn.close()

def get_latest_biz_logs(limit=100):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 检查表是否存在以防首次运行报错
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='biz_logs'")
    if not cursor.fetchone():
        conn.close()
        return []

    cursor.execute("SELECT * FROM biz_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    logs = []
    for r in rows:
        logs.append({
            "id": r[0],
            "ts": r[1],
            "level": r[2],
            "event": r[3],
            "device_id": r[4],
            "message": r[5],
            "extra": json.loads(r[6]) if r[6] else {}
        })
    return logs

def get_biz_logs_by_page(page=1, page_size=20):
    """
    分页查询业务日志
    :param page: 页码（从1开始）
    :param page_size: 每页条数
    :return: {logs: 日志列表, total: 总条数, total_pages: 总页数}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='biz_logs'")
    if not cursor.fetchone():
        conn.close()
        return {"logs": [], "total": 0, "total_pages": 0}
    
    # 查询总条数
    cursor.execute("SELECT COUNT(*) FROM biz_logs")
    total = cursor.fetchone()[0]
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    # 分页查询日志（按ID倒序，最新的在前）
    offset = (page - 1) * page_size
    cursor.execute("""
        SELECT * FROM biz_logs 
        ORDER BY id DESC 
        LIMIT ? OFFSET ?
    """, (page_size, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        logs.append({
            "id": r[0],
            "ts": r[1],
            "level": r[2],
            "event": r[3],
            "device_id": r[4],
            "message": r[5],
            "extra": json.loads(r[6]) if r[6] else {}
        })
    
    return {
        "logs": logs,
        "total": total,
        "total_pages": total_pages
    }

# =========================
# 统一日志接口
# =========================
def log_event(level, event, category, module, message, device_id=None, request_id=None,
              sid=None, topic=None, error=None, extra=None):
    ts = datetime.utcnow().isoformat() + "Z"
    log_data = {
        "ts": ts,
        "level": level,
        "event": event,
        "category": category,
        "module": module,
        "message": message
    }
    if device_id:
        log_data["device_id"] = device_id
    if request_id:
        log_data["request_id"] = request_id
    if sid:
        log_data["sid"] = sid
    if topic:
        log_data["topic"] = topic
    if error:
        log_data["error"] = str(error)
    if extra:
        log_data.update(extra)

    # 写到日志文件
    getattr(logger, level.lower(), logger.info)(json.dumps(log_data, ensure_ascii=False))

    # Biz 日志写入 SQLite
    if category == "biz":
        save_biz_log(ts, level, event, device_id, message, extra)
