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
READABLE_LOG_FILE = os.path.join(LOG_DIR, "readable.log")

# =========================
# logger 对象
# =========================
logger = logging.getLogger("forklift")
logger.setLevel(logging.DEBUG)  # DEBUG 级别可在开发时打开
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def append_readable_log(ts, level, event, category, module, message, device_id=None,
                        request_id=None, sid=None, topic=None, error=None, extra=None):
    """追加一份便于直接阅读的纯文本日志。"""
    parts = [
        f"[{ts}]",
        level,
        f"{category}/{module}",
        event,
    ]
    if device_id:
        parts.append(f"device={device_id}")
    if request_id:
        parts.append(f"request_id={request_id}")
    if sid:
        parts.append(f"sid={sid}")
    if topic:
        parts.append(f"topic={topic}")

    line = " | ".join(parts) + f" | {message}"
    if error:
        line += f" | error={error}"
    if extra:
        line += f" | extra={json.dumps(extra, ensure_ascii=False, sort_keys=True)}"

    with open(READABLE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# =========================
# Biz 日志入库
# =========================
def save_log(ts, level, event, category, device_id, message, extra=None):
    """
    保存日志到 SQLite 数据库（支持 ops/biz/sec 所有分类）
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS all_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            event TEXT,
            category TEXT,
            device_id TEXT,
            message TEXT,
            extra TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO all_logs (ts, level, event, category, device_id, message, extra)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ts, level, event, category, device_id, message, json.dumps(extra, ensure_ascii=False) if extra else None))
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

def get_logs_by_page(page=1, page_size=20, level=None, device_id=None, category=None):
    """
    分页查询日志（支持 ops/biz/sec 所有分类）
    :param page: 页码（从1开始）
    :param page_size: 每页条数
    :param level: 日志级别筛选（可选，如 INFO/WARNING/ERROR）
    :param device_id: 设备ID筛选（可选）
    :param category: 分类筛选（可选，ops/biz/sec）
    :return: {logs: 日志列表, total: 总条数, total_pages: 总页数}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='all_logs'")
    if not cursor.fetchone():
        conn.close()
        return {"logs": [], "total": 0, "total_pages": 0}
    
    # 构建 WHERE 条件
    conditions = []
    params = []
    if level:
        conditions.append("level = ?")
        params.append(level)
    if device_id:
        conditions.append("device_id = ?")
        params.append(device_id)
    if category:
        conditions.append("category = ?")
        params.append(category)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # 查询总条数
    cursor.execute(f"SELECT COUNT(*) FROM all_logs WHERE {where_clause}", params)
    total = cursor.fetchone()[0]
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    # 分页查询日志（按ID倒序，最新的在前）
    offset = (page - 1) * page_size
    query = f"""
        SELECT * FROM all_logs
        WHERE {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [page_size, offset])
    
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        logs.append({
            "id": r[0],
            "ts": r[1],
            "level": r[2],
            "event": r[3],
            "category": r[4],
            "device_id": r[5],
            "message": r[6],
            "extra": json.loads(r[7]) if r[7] else {}
        })
    
    return {
        "logs": logs,
        "total": total,
        "total_pages": total_pages
    }


# 兼容旧接口别名
def get_biz_logs_by_page(page=1, page_size=20, level=None, device_id=None):
    """兼容旧接口：默认查询 biz 日志"""
    return get_logs_by_page(page, page_size, level, device_id, category="biz")

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
    append_readable_log(
        ts,
        level,
        event,
        category,
        module,
        message,
        device_id=device_id,
        request_id=request_id,
        sid=sid,
        topic=topic,
        error=error,
        extra=extra,
    )

    # 所有分类日志都写入 SQLite（ops/biz/sec）
    save_log(ts, level, event, category, device_id, message, extra)
