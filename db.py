"""
SQLite 数据访问与表初始化
"""

import sqlite3
from datetime import datetime

DB_NAME = "alarm.db"

def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表结构，包含离线检测所需的字段"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 报警明细表：记录每次报警的快照
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
    
    # 设备状态表：维护每个设备的最新在线状态和最后看到时间
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            last_seen TEXT,
            online_status INTEGER DEFAULT 0,
            alarm INTEGER DEFAULT 0,
            driver_present INTEGER DEFAULT 0,
            outer_intrusion INTEGER DEFAULT 0,
            last_timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def update_device_status(device_id, alarm, timestamp, driver_present, outer_intrusion):
    """
    当收到 MQTT 消息时，更新设备状态表并插入报警明细
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 插入报警历史明细
    cursor.execute("""
        INSERT INTO alarms (device_id, alarm, timestamp, driver_present, outer_intrusion)
        VALUES (?, ?, ?, ?, ?)
    """, (device_id, alarm, timestamp, driver_present, outer_intrusion))
    
    # 2. 更新或插入设备最新状态（设置在线状态为 1）
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO devices (device_id, last_seen, online_status, alarm, driver_present, outer_intrusion, last_timestamp)
        VALUES (?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            last_seen = excluded.last_seen,
            online_status = 1,
            alarm = excluded.alarm,
            driver_present = excluded.driver_present,
            outer_intrusion = excluded.outer_intrusion,
            last_timestamp = excluded.last_timestamp
    """, (device_id, now_str, alarm, driver_present, outer_intrusion, timestamp))
    
    conn.commit()
    conn.close()

def set_device_offline(device_id):
    """将特定设备标记为离线"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE devices SET online_status = 0 WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()

def get_all_devices():
    """获取所有设备的当前状态列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_status():
    """获取所有设备的最新状态（兼容旧接口名）"""
    return get_all_devices()

def get_history(limit=50):
    """获取最近的历史记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alarms ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
