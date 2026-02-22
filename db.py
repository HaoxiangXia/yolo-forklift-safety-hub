"""
SQLite 数据访问与表初始化 - 增加趋势统计功能
"""

import sqlite3
from datetime import datetime

from config import DB_PATH, HISTORY_LIMIT, TREND_LIMIT

def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 报警明细表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            alarm INTEGER,
            timestamp TEXT
        )
    """)
    
    # 设备状态表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE,
            alarm_status INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            boot_time TEXT,
            last_seen TEXT,
            online_status INTEGER DEFAULT 0,
            update_time TEXT
        )
    """)
    conn.commit()
    conn.close()

def update_device_data(device_id, alarm):
    """
    更新设备数据并插入历史记录
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 插入历史明细表
    cursor.execute("""
        INSERT INTO alarms (device_id, alarm, timestamp)
        VALUES (?, ?, ?)
    """, (device_id, alarm, now_str))
    
    # 2. 更新设备实时状态逻辑
    cursor.execute("SELECT alarm_status, online_status, error_count, boot_time FROM devices WHERE device_id = ?", (device_id,))
    row = cursor.fetchone()
    
    if row:
        old_alarm = row['alarm_status']
        old_online = row['online_status']
        error_count = row['error_count']
        boot_time = row['boot_time']
        
        if old_online == 0:
            boot_time = now_str
            
        if old_alarm == 0 and alarm == 1:
            error_count += 1
            
        cursor.execute("""
            UPDATE devices SET
                alarm_status = ?,
                error_count = ?,
                boot_time = ?,
                last_seen = ?,
                online_status = 1,
                update_time = ?
            WHERE device_id = ?
        """, (alarm, error_count, boot_time, now_str, now_str, device_id))
    else:
        cursor.execute("""
            INSERT INTO devices (device_id, alarm_status, error_count, boot_time, last_seen, online_status, update_time)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (device_id, alarm, (1 if alarm == 1 else 0), now_str, now_str, now_str))
        
    conn.commit()
    conn.close()

def set_device_offline(device_id):
    """标记设备为离线"""
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

def get_latest_data_with_stats():
    """获取所有设备数据及统计信息"""
    devices = get_all_devices()
    total = len(devices)
    online = sum(1 for d in devices if d['online_status'] == 1)
    alarm = sum(1 for d in devices if d['alarm_status'] == 1 and d['online_status'] == 1)
    
    return {
        "devices": devices,
        "stats": {
            "total": total,
            "online": online,
            "alarm": alarm
        }
    }

def get_device_history_raw(device_id, limit=HISTORY_LIMIT):
    """获取原始最近记录，用于列表展示"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT alarm, timestamp 
        FROM alarms 
        WHERE device_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (device_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_device_alarm_trend(device_id, limit=TREND_LIMIT):
    """
    报警次数趋势聚合统计：
    1. 取最近 limit 条记录
    2. 按分钟分组统计 alarm=1 的次数
    3. 返回 labels(分钟) 和 counts(次数)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 子查询取最近 limit 条，外部查询进行分钟级聚合
    query = """
        SELECT 
            strftime('%H:%M', timestamp) as minute,
            SUM(CASE WHEN alarm = 1 THEN 1 ELSE 0 END) as alarm_count
        FROM (
            SELECT alarm, timestamp 
            FROM alarms 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        )
        GROUP BY minute
        ORDER BY minute ASC
    """
    cursor.execute(query, (device_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    labels = [row['minute'] for row in rows]
    counts = [row['alarm_count'] for row in rows]
    
    return {
        "labels": labels,
        "counts": counts
    }
