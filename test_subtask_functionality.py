#!/usr/bin/env python3
"""
子任务功能测试脚本
用于验证树形结构的完整功能
"""

import requests
import json

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def test_subtask_functionality():
    print("=== 子任务功能测试 ===\n")
    
    # 1. 注册新用户
    print("1. 注册用户...")
    register_data = {
        "username": "subtask_tester",
        "email": "subtask@test.com", 
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", 
                               json=register_data, 
                               headers=HEADERS)
        if response.status_code in [200, 201]:
            print("✓ 用户注册成功")
        elif response.status_code == 400 and "用户名已存在" in response.text:
            print("✓ 用户已存在，跳过注册")
        else:
            print(f"✗ 注册失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 注册异常: {e}")
        return
    
    # 2. 登录获取token
    print("\n2. 用户登录...")
    login_data = {
        "username": "subtask_tester",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
                               json=login_data, 
                               headers=HEADERS)
        if response.status_code == 200:
            token = response.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}", **HEADERS}
            print("✓ 登录成功，获得访问令牌")
        else:
            print(f"✗ 登录失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 登录异常: {e}")
        return
    
    # 3. 创建根任务
    print("\n3. 创建根任务...")
    root_todo_data = {
        "title": "项目规划",
        "description": "完整的项目规划任务",
        "category": "工作",
        "priority": "high"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/todos/", 
                               json=root_todo_data, 
                               headers=auth_headers)
        if response.status_code in [200, 201]:
            root_todo = response.json()
            root_id = root_todo["id"]
            print(f"✓ 根任务创建成功 (ID: {root_id})")
        else:
            print(f"✗ 根任务创建失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 根任务创建异常: {e}")
        return
    
    # 4. 创建子任务
    print("\n4. 创建子任务...")
    subtask1_data = {
        "title": "需求分析",
        "description": "分析用户需求和功能要求",
        "category": "分析",
        "priority": "high"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/subtasks/{root_id}/children", 
                               json=subtask1_data, 
                               headers=auth_headers)
        if response.status_code in [200, 201]:
            subtask1 = response.json()
            subtask1_id = subtask1["id"]
            print(f"✓ 子任务1创建成功 (ID: {subtask1_id})")
        else:
            print(f"✗ 子任务1创建失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 子任务1创建异常: {e}")
        return
    
    # 5. 创建孙子任务
    print("\n5. 创建孙子任务...")
    grandchild_data = {
        "title": "用户调研",
        "description": "进行用户访谈和调研",
        "category": "调研",
        "priority": "medium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/subtasks/{subtask1_id}/children", 
                               json=grandchild_data, 
                               headers=auth_headers)
        if response.status_code in [200, 201]:
            grandchild = response.json()
            grandchild_id = grandchild["id"]
            print(f"✓ 孙子任务创建成功 (ID: {grandchild_id})")
        else:
            print(f"✗ 孙子任务创建失败: {response.text}")
            return
    except Exception as e:
        print(f"✗ 孙子任务创建异常: {e}")
        return
    
    # 6. 获取任务树
    print("\n6. 获取任务树结构...")
    try:
        response = requests.get(f"{BASE_URL}/api/subtasks/{root_id}/tree", 
                              headers=auth_headers)
        if response.status_code in [200, 201]:
            tree_data = response.json()
            print("✓ 任务树获取成功")
            print(f"  树深度: {tree_data['depth']}")
            print(f"  总节点数: {tree_data['total_nodes']}")
            
            # 显示树结构
            def print_tree(node, level=0):
                indent = "  " * level
                print(f"{indent}- {node['title']} (ID: {node['id']})")
                for child in node.get('children', []):
                    print_tree(child, level + 1)
            
            print("  树结构:")
            print_tree(tree_data['root'])
        else:
            print(f"✗ 任务树获取失败: {response.text}")
    except Exception as e:
        print(f"✗ 任务树获取异常: {e}")
    
    # 7. 测试任务移动
    print("\n7. 测试任务移动...")
    # 创建另一个根任务用于移动测试
    move_target_data = {
        "title": "另一个项目",
        "description": "用于测试移动功能",
        "category": "工作",
        "priority": "medium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/todos/", 
                               json=move_target_data, 
                               headers=auth_headers)
        if response.status_code in [200, 201]:
            move_target = response.json()
            move_target_id = move_target["id"]
            print(f"✓ 移动目标任务创建成功 (ID: {move_target_id})")
            
            # 尝试将孙子任务移动到新根任务下
            move_data = {"new_parent_id": move_target_id}
            response = requests.put(f"{BASE_URL}/api/subtasks/{grandchild_id}/move", 
                                  json=move_data, 
                                  headers=auth_headers)
            if response.status_code in [200, 201]:
                print("✓ 任务移动成功")
            else:
                print(f"✗ 任务移动失败: {response.text}")
        else:
            print(f"✗ 移动目标任务创建失败: {response.text}")
    except Exception as e:
        print(f"✗ 任务移动测试异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_subtask_functionality()