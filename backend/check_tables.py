import sqlite3

# 连接数据库
conn = sqlite3.connect('./todo_app.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("数据库中的表:")
for table in tables:
    print(f"- {table[0]}")

# 查看offline_operations表结构
if any(table[0] == 'offline_operations' for table in tables):
    print("\noffline_operations表结构:")
    cursor.execute("PRAGMA table_info(offline_operations);")
    columns = cursor.fetchall()
    for col in columns:
        print(f"- {col[1]} ({col[2]})")

# 查看todos表结构
if any(table[0] == 'todos' for table in tables):
    print("\ntodos表结构:")
    cursor.execute("PRAGMA table_info(todos);")
    columns = cursor.fetchall()
    for col in columns:
        print(f"- {col[1]} ({col[2]})")

conn.close()