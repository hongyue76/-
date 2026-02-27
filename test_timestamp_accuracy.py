#!/usr/bin/env python3
"""
时间戳准确性测试 - 验证LWW策略的时间戳可靠性
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_timestamp_accuracy():
    """测试时间戳准确性"""
    print("=== 时间戳准确性测试 ===\n")
    
    # 1. 注册测试用户
    username = f"timestamp_test_{int(time.time())}"
    user_data = {
        "username": username,
        "email": f"{username}@test.com",
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code not in [200, 201]:
        print(f"✗ 用户注册失败: {response.text}")
        return
    
    # 2. 用户登录
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": "password123"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ 用户登录成功")
    
    # 3. 创建测试任务
    task_data = {
        "title": "时间戳测试任务",
        "description": "用于测试LWW时间戳准确性",
        "priority": "medium"
    }
    
    create_response = requests.post(f"{BASE_URL}/todos/", json=task_data, headers=headers)
    task_id = create_response.json()["id"]
    print(f"✓ 任务创建成功 (ID: {task_id})")
    
    # 4. 模拟恶意客户端时间戳攻击
    print("\n4. 测试恶意时间戳攻击防护...")
    
    # 客户端伪造未来时间戳
    fake_future_time = datetime(2030, 1, 1, 12, 0, 0)
    
    malicious_operation = {
        "todo_id": task_id,
        "operation_type": "UPDATE",
        "field_name": "title",
        "old_value": "时间戳测试任务",
        "new_value": "恶意修改-伪造时间戳",
        "timestamp": fake_future_time.isoformat(),
        "device_id": "malicious_device"
    }
    
    # 记录恶意操作
    record_response = requests.post(f"{BASE_URL}/offline/operations", json=malicious_operation, headers=headers)
    print("✓ 恶意操作已记录")
    
    # 5. 正常客户端操作（稍后执行）
    time.sleep(1)  # 确保真实时间晚于恶意时间
    
    normal_operation = {
        "todo_id": task_id,
        "operation_type": "UPDATE",
        "field_name": "title",
        "old_value": "时间戳测试任务",
        "new_value": "正常修改-真实时间",
        "device_id": "normal_device"
    }
    
    # 记录正常操作
    requests.post(f"{BASE_URL}/offline/operations", json=normal_operation, headers=headers)
    print("✓ 正常操作已记录")
    
    # 6. 执行同步测试
    print("\n6. 执行同步测试...")
    
    # 恶意客户端先同步
    malicious_sync = {
        "last_sync_time": None,
        "device_id": "malicious_device",
        "pending_operations": [malicious_operation]
    }
    
    malicious_sync_response = requests.post(f"{BASE_URL}/offline/sync", json=malicious_sync, headers=headers)
    print("✓ 恶意客户端同步完成")
    
    # 正常客户端后同步
    normal_sync = {
        "last_sync_time": None,
        "device_id": "normal_device",
        "pending_operations": [normal_operation]
    }
    
    normal_sync_response = requests.post(f"{BASE_URL}/offline/sync", json=normal_sync, headers=headers)
    
    # 7. 验证结果
    print("\n7. 验证时间戳保护效果...")
    
    if normal_sync_response.json().get("conflicts"):
        conflict = normal_sync_response.json()["conflicts"][0]
        print("✓ 成功检测到时间戳冲突！")
        print(f"  冲突详情: {conflict}")
        
        # 检查时间戳信息
        server_ts = conflict.get("server_timestamp")
        task_ts = conflict.get("task_updated_at")
        
        if server_ts and task_ts:
            print(f"  服务器时间戳: {server_ts}")
            print(f"  任务更新时间: {task_ts}")
            
            # 验证服务器时间戳确实晚于恶意时间戳
            server_time = datetime.fromisoformat(server_ts.replace('Z', '+00:00'))
            malicious_time = fake_future_time
            
            if server_time > malicious_time:
                print("✓ 服务器时间戳正确识别了恶意时间戳")
                print("✓ LWW策略有效防止了时间欺骗攻击")
            else:
                print("⚠ 时间戳验证异常")
    
    # 8. 最终验证
    final_task = requests.get(f"{BASE_URL}/todos/{task_id}", headers=headers).json()
    print(f"\n✓ 最终任务标题: {final_task['title']}")
    
    # 预期结果应该是正常修改，因为服务器时间戳更准确
    if "正常修改" in final_task['title']:
        print("🎉 测试成功：服务器时间戳有效防止了恶意时间欺骗！")
    else:
        print("❌ 测试失败：恶意时间戳影响了最终结果")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_timestamp_accuracy()