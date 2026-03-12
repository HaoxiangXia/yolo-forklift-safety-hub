"""
SQLite 数据访问与表初始化 - 增加趋势统计功能
"""

import sqlite3
import json
import os
import base64
from datetime import datetime

from config import DB_PATH, HISTORY_LIMIT, TREND_LIMIT, DB_BUSY_TIMEOUT_MS

# 图片存储目录
IMAGE_DIR = "images/alarms"
os.makedirs(IMAGE_DIR, exist_ok=True)

def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 使用 WAL 让读写并发更友好，读请求不会轻易被写事务阻塞。
    conn.execute("PRAGMA journal_mode=WAL;")
    # 设置 busy_timeout 后，遇到锁竞争会等待一段时间，降低 database is locked 概率。
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS};")
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
            update_time TEXT,
            pos_x REAL DEFAULT 0,
            pos_y REAL DEFAULT 0
        )
    """)

    # 数据库迁移：添加缺失的列（如果表已存在）
    try:
        cursor.execute("ALTER TABLE devices ADD COLUMN pos_x REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    try:
        cursor.execute("ALTER TABLE devices ADD COLUMN pos_y REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 业务日志表 (由 V1 引入)
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

    # 报警图片表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarm_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            image_path TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

def update_device_data(device_id, alarm):
    """
    更新设备数据并插入历史记录。
    返回变更状态字典，供日志使用。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed = {}
    
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
            changed['online_marked'] = True
            
        if old_alarm == 0 and alarm == 1:
            error_count += 1
            changed['alarm_raised'] = True

        if old_alarm == 1 and alarm == 0:
            changed['alarm_cleared'] = True
            
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
        changed['online_marked'] = True
        if alarm == 1:
            changed['alarm_raised'] = True
        
    conn.commit()
    conn.close()
    return changed

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

def save_alarm_image(device_id, image_path, timestamp):
    """保存报警图片记录到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alarm_images (device_id, image_path, timestamp)
        VALUES (?, ?, ?)
    """, (device_id, image_path, timestamp))
    conn.commit()
    conn.close()

def get_device_images(device_id, limit=20):
    """获取设备的报警图片列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, image_path, timestamp
        FROM alarm_images
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (device_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_image(device_id):
    """获取设备的最新报警图片"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT image_path, timestamp
        FROM alarm_images
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (device_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_base64_image(device_id, base64_data, timestamp):
    """
    保存 base64 编码的图片到文件系统
    :param device_id: 设备ID
    :param base64_data: base64 编码的图片数据
    :param timestamp: 时间戳字符串
    :return: 保存的文件路径
    """
    try:
        # 解析 data URL 格式 (data:image/jpeg;base64,...)
        if "," in base64_data:
            header, base64_data = base64_data.split(",", 1)
        
        # 解码 base64
        image_bytes = base64.b64decode(base64_data)
        
        # 生成文件名
        safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
        filename = f"{device_id}_{safe_timestamp}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 写入文件
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        # 保存到数据库
        save_alarm_image(device_id, filepath, timestamp)
        
        return filepath
    except Exception as e:
        print(f"[错误] 保存报警图片失败: {e}")
        return None

def init_device_positions():
    """初始化设备位置（随机生成）"""
    import random
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取所有设备
    cursor.execute("SELECT device_id FROM devices")
    devices = cursor.fetchall()
    
    for dev in devices:
        device_id = dev['device_id']
        # 检查是否已有位置
        cursor.execute("SELECT pos_x, pos_y FROM devices WHERE device_id = ?", (device_id,))
        row = cursor.fetchone()
        if row and (row['pos_x'] is None or row['pos_x'] == 0):
            # 随机生成位置
            pos_x = random.uniform(0, 1920)
            pos_y = random.uniform(0, 1080)
            cursor.execute("UPDATE devices SET pos_x = ?, pos_y = ? WHERE device_id = ?",
                          (pos_x, pos_y, device_id))
    
    conn.commit()
    conn.close()

def update_device_position(device_id, pos_x, pos_y):
    """更新设备位置"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE devices SET pos_x = ?, pos_y = ? WHERE device_id = ?",
                  (pos_x, pos_y, device_id))
    conn.commit()
    conn.close()

def get_all_devices_with_positions():
    """获取所有设备及其位置"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT device_id, alarm_status, online_status, pos_x, pos_y, last_seen
        FROM devices
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recent_alarms(limit=5):
    """获取最近报警事件（关联图片）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.device_id, a.timestamp, a.alarm,
               (SELECT image_path FROM alarm_images ai
                WHERE ai.device_id = a.device_id
                ORDER BY ai.timestamp DESC LIMIT 1) as image_path
        FROM alarms a
        WHERE a.alarm = 1
        ORDER BY a.timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
