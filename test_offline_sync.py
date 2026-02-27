#!/usr/bin/env python3
"""
离线同步功能测试脚本
验证幂等性和操作合并机制
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def test_offline_sync():
    print("=== 离线同步功能测试 ===\n")
    
    # 1. 注册测试用户
    print("1. 注册测试用户...")
    register_data = {
        "username": "offline_tester",
        "email": "offline@test.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", 
                               json=register_data, 
                               headers=HEADERS)
        if response.status_code in [200, 201, 400]:
            print("✓ 用户准备完成")
        else:
            print(f"✗ 用户注册失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 用户注册异常: {e}")
        return
    
    # 2. 登录获取token
    print("\n2. 用户登录...")
    login_data = {
        "username": "offline_tester",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
                               json=login_data, 
                               headers=HEADERS)
        if response.status_code == 200:
            token = response.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}", **HEADERS}
            print("✓ 登录成功")
        else:
            print(f"✗ 登录失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 登录异常: {e}")
        return
    
    # 3. 创建测试任务
    print("\n3. 创建测试任务...")
    todo_data = {
        "title": "离线测试任务",
        "description": "用于测试离线同步功能",
        "category": "测试",
        "priority": "medium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/todos/", 
                               json=todo_data, 
                               headers=auth_headers)
        if response.status_code in [200, 201]:
            todo = response.json()
            todo_id = todo["id"]
            print(f"✓ 任务创建成功 (ID: {todo_id})")
        else:
            print(f"✗ 任务创建失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 任务创建异常: {e}")
        return
    
    # 4. 模拟离线操作 - 多次修改同一字段
    print("\n4. 模拟离线操作...")
    
    # 第一次修改
    operation1 = {
        "todo_id": todo_id,
        "operation_type": "UPDATE",
        "field_name": "title",
        "old_value": "离线测试任务",
        "new_value": "第一次修改",
        "device_id": "test_device_1"
    }
    
    # 第二次修改（覆盖第一次）
    operation2 = {
        "todo_id": todo_id,
        "operation_type": "UPDATE",
        "field_name": "title",
        "old_value": "第一次修改",
        "new_value": "第二次修改",
        "device_id": "test_device_1"
    }
    
    # 第三次修改不同的字段
    operation3 = {
        "todo_id": todo_id,
        "operation_type": "UPDATE",
        "field_name": "description",
        "old_value": "用于测试离线同步功能",
        "new_value": "最终描述内容",
        "device_id": "test_device_1"
    }
    
    sync_request = {
        "last_sync_time": None,
        "device_id": "test_device_1",
        "pending_operations": [operation1, operation2, operation3]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/offline/sync",
                               json=sync_request,
                               headers=auth_headers)
        if response.status_code == 200:
            sync_result = response.json()
            print("✓ 离线同步成功")
            print(f"  服务器更新数量: {len(sync_result.get('server_updates', []))}")
            print(f"  冲突数量: {len(sync_result.get('conflicts', []))}")
            
            # 验证最终结果
            response = requests.get(f"{BASE_URL}/api/todos/{todo_id}",
                                  headers=auth_headers)
            if response.status_code == 200:
                final_todo = response.json()
                print(f"  最终标题: {final_todo['title']}")
                print(f"  最终描述: {final_todo['description']}")
                
                # 验证幂等性 - 应该是最后一次修改的结果
                if final_todo['title'] == "第二次修改" and final_todo['description'] == "最终描述内容":
                    print("✓ 幂等性验证通过 - 正确保留了最后一次修改")
                else:
                    print("✗ 幂等性验证失败")
                    
        else:
            print(f"✗ 离线同步失败: {response.text}")
    except Exception as e:
        print(f"✗ 离线同步异常: {e}")
    
    # 5. 测试获取待处理操作
    print("\n5. 测试待处理操作查询...")
    try:
        response = requests.get(f"{BASE_URL}/api/offline/operations/pending",
                              headers=auth_headers)
        if response.status_code == 200:
            pending_ops = response.json()
            print(f"✓ 获取待处理操作成功，数量: {len(pending_ops)}")
        else:
            print(f"✗ 获取待处理操作失败: {response.text}")
    except Exception as e:
        print(f"✗ 获取待处理操作异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_offline_sync()