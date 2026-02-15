import sqlite3
from datetime import datetime

DB_NAME = "alarm.db"

def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表结构，包含新增的 driver_present 和 outer_intrusion 字段"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            alarm INTEGER,
            timestamp TEXT,
            driver_present INTEGER,
            outer_intrusion INTEGER
        )
    """)
    conn.commit()
    conn.close()

def insert_alarm_data(device_id, alarm, timestamp, driver_present, outer_intrusion):
    """插入一条完整的报警数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alarms (device_id, alarm, timestamp, driver_present, outer_intrusion)
        VALUES (?, ?, ?, ?, ?)
    """, (device_id, alarm, timestamp, driver_present, outer_intrusion))
    conn.commit()
    conn.close()

def get_latest_status():
    """获取所有设备最新的状态记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # 子查询：找到每个 device_id 对应的最大 ID
    query = """
        SELECT * FROM alarms 
        WHERE id IN (
            SELECT MAX(id) FROM alarms GROUP BY device_id
        )
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    # 将 sqlite3.Row 对象转换为普通字典列表，方便 Flask 返回 JSON
    return [dict(row) for row in rows]

def get_history(limit=50):
    """获取最近的历史记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alarms ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
