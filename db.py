"""
SQLite 数据访问与表初始化 - 升级统计功能
"""

import sqlite3
import time
from datetime import datetime

DB_NAME = "alarm.db"

def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """重新设计数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 核心设备状态表
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
    当收到 MQTT 消息时更新设备数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 查询该设备当前状态
    cursor.execute("SELECT alarm_status, online_status, error_count, boot_time FROM devices WHERE device_id = ?", (device_id,))
    row = cursor.fetchone()
    
    if row:
        old_alarm = row['alarm_status']
        old_online = row['online_status']
        error_count = row['error_count']
        boot_time = row['boot_time']
        
        # 逻辑：如果之前离线，现在上线，则重置 boot_time
        if old_online == 0:
            boot_time = now_str
            
        # 逻辑：当 alarm_status 从 0 变为 1 时，error_count + 1
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
        # 新设备首次上线
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
    """
    获取所有设备数据，并计算统计信息
    返回格式: { devices: [...], stats: { total: X, online: Y, alarm: Z } }
    """
    devices = get_all_devices()
    total = len(devices)
    online = sum(1 for d in devices if d['online_status'] == 1)
    # 只有在线且报警的才算作当前报警设备
    alarm = sum(1 for d in devices if d['alarm_status'] == 1 and d['online_status'] == 1)
    
    return {
        "devices": devices,
        "stats": {
            "total": total,
            "online": online,
            "alarm": alarm
        }
    }

def get_latest_status():
    """兼容旧接口"""
    return get_all_devices()
