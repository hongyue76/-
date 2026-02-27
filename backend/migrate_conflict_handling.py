#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加冲突处理相关字段
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """执行数据库迁移"""
    print("开始数据库迁移...")
    
    # 数据库文件路径
    db_path = Path("./todo_app.db")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查todos表是否已有conflict_details字段
        cursor.execute("PRAGMA table_info(todos)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'conflict_details' not in columns:
            print("添加 conflict_details 字段...")
            cursor.execute("ALTER TABLE todos ADD COLUMN conflict_details TEXT")
            conn.commit()
            print("✓ conflict_details 字段添加成功")
        else:
            print("✓ conflict_details 字段已存在")
        
        # 检查offline_operations表结构
        cursor.execute("PRAGMA table_info(offline_operations)")
        op_columns = [row[1] for row in cursor.fetchall()]
        
        required_fields = ['old_value', 'sequence_id']
        for field in required_fields:
            if field not in op_columns:
                print(f"警告: 缺少字段 {field}")
            else:
                print(f"✓ {field} 字段已存在")
        
        conn.close()
        print("数据库迁移完成！")
        return True
        
    except Exception as e:
        print(f"迁移失败: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)