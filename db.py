"""
SQLite 数据访问与表初始化 - 设备状态管理系统
整合功能：设备状态更新、离线标记、统计查询、兼容旧接口
"""

import sqlite3
from datetime import datetime

# 统一数据库配置（可根据实际需求修改）
DB_PATH = "alarm.db"  # 选用第二段的数据库名，也可改为 data.db

def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表结构（包含设备表和业务日志表）"""
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
    
    # 业务日志表（保留第一段的表结构）
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
    
    conn.commit()
    conn.close()

def update_device_data(device_id, alarm):
    """
    当收到 MQTT 消息时更新设备数据
    :param device_id: 设备ID
    :param alarm: 告警状态（0=无告警，1=有告警）
    :return: 状态变更字典，包含 online_marked/alarm_raised/alarm_cleared 等标识
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed = {}  # 记录状态变更
    
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
            changed['online_marked'] = True
        
        # 逻辑：当 alarm_status 从 0 变为 1 时，error_count + 1
        if old_alarm == 0 and alarm == 1:
            error_count += 1
            changed['alarm_raised'] = True
        
        # 逻辑：当告警从1变为0时，标记告警已清除
        if old_alarm == 1 and alarm == 0:
            changed['alarm_cleared'] = True
        
        # 更新设备状态
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
        
        changed['online_marked'] = True
        if alarm == 1:
            changed['alarm_raised'] = True
    
    conn.commit()
    conn.close()
    return changed

def set_device_offline(device_id):
    """标记设备为离线状态"""
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
    """兼容旧接口：仅返回所有设备状态列表（等同于 get_all_devices）"""
    return get_all_devices()

# 测试代码（可选，用于验证功能）
if __name__ == "__main__":
    # 初始化数据库
    init_db()
    
    # 更新设备状态
    print(update_device_data("device_001", 1))  # 新设备告警上线
    print(update_device_data("device_001", 0))  # 告警清除
    print(update_device_data("device_002", 0))  # 新设备正常上线
    
    # 标记设备离线
    set_device_offline("device_002")
    
    # 查询统计信息
    print(get_latest_data_with_stats())
