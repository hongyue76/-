#!/usr/bin/env python3
"""
添加时间戳相关字段的迁移脚本
"""

import sqlite3
from pathlib import Path

def migrate_timestamp_fields():
    """为offline_operations表添加时间戳字段"""
    print("开始添加时间戳字段迁移...")
    
    # 数据库文件路径
    db_path = Path("./todo_app.db")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查offline_operations表结构
        cursor.execute("PRAGMA table_info(offline_operations)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 添加缺失的字段
        fields_to_add = [
            ("client_timestamp", "DATETIME"),
            ("server_timestamp", "DATETIME"),
            ("logical_timestamp", "INTEGER")
        ]
        
        for field_name, field_type in fields_to_add:
            if field_name not in columns:
                print(f"添加字段: {field_name} {field_type}")
                cursor.execute(f"ALTER TABLE offline_operations ADD COLUMN {field_name} {field_type}")
            else:
                print(f"✓ 字段已存在: {field_name}")
        
        conn.commit()
        conn.close()
        print("✓ 时间戳字段迁移完成！")
        return True
        
    except Exception as e:
        print(f"迁移失败: {e}")
        return False

if __name__ == "__main__":
    migrate_timestamp_fields()