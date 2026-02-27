#!/usr/bin/env python3
"""
冲突处理功能测试脚本
模拟两个用户同时编辑同一任务的场景
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_conflict_handling():
    """测试冲突处理功能"""
    print("=== 冲突处理功能测试 ===\n")
    
    # 1. 注册测试用户
    print("1. 注册测试用户...")
    user1_data = {
        "username": f"user1_conflict_{int(datetime.now().timestamp())}",
        "email": f"user1_{int(datetime.now().timestamp())}@test.com",
        "password": "password123"
    }
    
    user2_data = {
        "username": f"user2_conflict_{int(datetime.now().timestamp())}", 
        "email": f"user2_{int(datetime.now().timestamp())}@test.com",
        "password": "password123"
    }
    
    # 注册用户1
    response = requests.post(f"{BASE_URL}/auth/register", json=user1_data)
    if response.status_code in [200, 201]:
        print("✓ 用户1注册成功")
    else:
        print(f"✗ 用户1注册失败: {response.text}")
        return
    
    # 注册用户2
    response = requests.post(f"{BASE_URL}/auth/register", json=user2_data)
    if response.status_code in [200, 201]:
        print("✓ 用户2注册成功")
    else:
        print(f"✗ 用户2注册失败: {response.text}")
        return
    
    # 2. 用户登录
    print("\n2. 用户登录...")
    login1_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": user1_data["username"],
        "password": "password123"
    })
    print(f"用户1登录响应: {login1_response.text}")
    token1 = login1_response.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    print("✓ 用户1登录成功")
    
    login2_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": user2_data["username"],
        "password": "password123"
    })
    print(f"用户2登录响应: {login2_response.text}")
    token2 = login2_response.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    print("✓ 用户2登录成功")
    
    # 3. 用户1创建任务
    print("\n3. 用户1创建测试任务...")
    task_data = {
        "title": "购物清单",
        "description": "需要购买的日用品",
        "priority": "medium"  # 小写优先级
    }
    
    create_response = requests.post(f"{BASE_URL}/todos/", json=task_data, headers=headers1)
    print(f"创建任务响应: {create_response.text}")
    
    if create_response.status_code not in [200, 201]:
        print("✗ 任务创建失败")
        return
        
    task_response = create_response.json()
    task_id = task_response.get("id") or task_response.get("data", {}).get("id")
    if not task_id:
        print("✗ 无法获取任务ID")
        return
    print(f"✓ 任务创建成功 (ID: {task_id})")
    
    # 4. 模拟并发编辑冲突
    print("\n4. 模拟并发编辑冲突...")
    
    # 用户1离线修改标题为"买菜"
    offline_op1 = {
        "todo_id": task_id,
        "operation_type": "UPDATE",
        "field_name": "title",
        "old_value": "购物清单",
        "new_value": "买菜",
        "device_id": "device1"
    }
    
    # 用户2离线修改标题为"购物"
    offline_op2 = {
        "todo_id": task_id,
        "operation_type": "UPDATE", 
        "field_name": "title",
        "old_value": "购物清单",
        "new_value": "购物",
        "device_id": "device2"
    }
    
    # 记录两个操作
    requests.post(f"{BASE_URL}/offline/operations", json=offline_op1, headers=headers1)
    requests.post(f"{BASE_URL}/offline/operations", json=offline_op2, headers=headers2)
    print("✓ 两个并发操作已记录")
    
    # 5. 用户1先同步（应该成功）
    print("\n5. 用户1执行同步...")
    sync_request1 = {
        "last_sync_time": None,
        "device_id": "device1",
        "pending_operations": [offline_op1]
    }
    
    sync_response1 = requests.post(f"{BASE_URL}/offline/sync", json=sync_request1, headers=headers1)
    print(f"✓ 用户1同步完成，服务器标题: {sync_response1.json()['server_updates'][0]['title']}")
    
    # 6. 用户2后同步（应该检测到冲突）
    print("\n6. 用户2执行同步（预期产生冲突）...")
    sync_request2 = {
        "last_sync_time": None,
        "device_id": "device2", 
        "pending_operations": [offline_op2]
    }
    
    sync_response2 = requests.post(f"{BASE_URL}/offline/sync", json=sync_request2, headers=headers2)
    
    if sync_response2.json().get("conflicts"):
        conflict = sync_response2.json()["conflicts"][0]
        print("✓ 成功检测到冲突！")
        print(f"  冲突详情: {conflict}")
        
        # 7. 测试冲突解决
        print("\n7. 测试冲突解决...")
        
        # 选择智能合并策略
        resolution = {
            "operation_id": conflict.get("operation_id", 1),
            "resolution": "merge",
            "merged_data": {"title": "买菜 & 购物"}
        }
        
        resolve_response = requests.post(f"{BASE_URL}/offline/resolve-conflict", json=resolution, headers=headers2)
        print("✓ 冲突解决完成")
        
        # 验证最终结果
        final_task = requests.get(f"{BASE_URL}/todos/{task_id}", headers=headers1).json()
        print(f"✓ 最终任务标题: {final_task['title']}")
        
    else:
        print("⚠ 未检测到预期的冲突")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_conflict_handling()