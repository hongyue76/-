"""
共享清单权限控制服务
实现细粒度的隐私边界管理
"""

from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

class PermissionLevel(Enum):
    """权限等级定义"""
    OWNER = "owner"          # 所有者：完全访问权限
    ADMIN = "admin"          # 管理员：可管理成员和设置
    EDITOR = "editor"        # 编辑者：可编辑任务，有限历史查看
    VIEWER = "viewer"        # 查看者：只读权限，基本历史查看
    COMMENTER = "commenter"  # 评论者：可评论，最小历史查看

class HistoryVisibility(Enum):
    """历史记录可见性级别"""
    FULL = "full"           # 完整历史（包括操作者身份）
    ANONYMIZED = "anonymized"  # 匿名历史（隐藏操作者身份）
    SUMMARY = "summary"     # 概要历史（仅显示关键变更）
    NONE = "none"           # 无历史记录

class PrivacyBoundary:
    """隐私边界控制器"""
    
    def __init__(self):
        # 权限映射表
        self.permission_matrix = {
            PermissionLevel.OWNER: {
                'view_history': HistoryVisibility.FULL,
                'view_comments': True,
                'edit_tasks': True,
                'manage_members': True,
                'delete_list': True
            },
            PermissionLevel.ADMIN: {
                'view_history': HistoryVisibility.ANONYMIZED,
                'view_comments': True,
                'edit_tasks': True,
                'manage_members': True,
                'delete_list': False
            },
            PermissionLevel.EDITOR: {
                'view_history': HistoryVisibility.SUMMARY,
                'view_comments': True,
                'edit_tasks': True,
                'manage_members': False,
                'delete_list': False
            },
            PermissionLevel.VIEWER: {
                'view_history': HistoryVisibility.SUMMARY,
                'view_comments': True,
                'edit_tasks': False,
                'manage_members': False,
                'delete_list': False
            },
            PermissionLevel.COMMENTER: {
                'view_history': HistoryVisibility.NONE,
                'view_comments': True,
                'edit_tasks': False,
                'manage_members': False,
                'delete_list': False
            }
        }
    
    def get_history_visibility(self, user_role: PermissionLevel) -> HistoryVisibility:
        """获取用户的历史记录可见性"""
        return self.permission_matrix[user_role]['view_history']
    
    def can_view_full_history(self, user_role: PermissionLevel) -> bool:
        """检查是否可查看完整历史"""
        return self.get_history_visibility(user_role) == HistoryVisibility.FULL
    
    def get_anonymized_history(self, full_history: List[Dict]) -> List[Dict]:
        """获取匿名化的历史记录"""
        anonymized = []
        for record in full_history:
            anonymized_record = {
                'id': record['id'],
                'task_id': record['task_id'],
                'field_name': record['field_name'],
                'old_value': record['old_value'],
                'new_value': record['new_value'],
                'timestamp': record['timestamp'],
                'change_type': record['change_type'],
                # 隐藏操作者身份
                'operator': '协作者' if record.get('operator') else '系统'
            }
            anonymized.append(anonymized_record)
        return anonymized
    
    def get_summary_history(self, full_history: List[Dict]) -> List[Dict]:
        """获取概要历史记录"""
        summary = []
        # 按任务分组，只显示关键变更
        task_changes = {}
        
        for record in full_history:
            task_id = record['task_id']
            if task_id not in task_changes:
                task_changes[task_id] = {
                    'task_id': task_id,
                    'title': record.get('task_title', '未知任务'),
                    'major_changes': [],
                    'last_modified': record['timestamp']
                }
            
            # 只记录重要字段的变更
            important_fields = ['title', 'completed', 'priority', 'due_date']
            if record['field_name'] in important_fields:
                task_changes[task_id]['major_changes'].append({
                    'field': record['field_name'],
                    'change': f"{record['old_value']} → {record['new_value']}",
                    'time': record['timestamp']
                })
            
            # 更新最后修改时间
            if record['timestamp'] > task_changes[task_id]['last_modified']:
                task_changes[task_id]['last_modified'] = record['timestamp']
        
        # 转换为摘要格式
        for task_data in task_changes.values():
            if task_data['major_changes']:  # 只显示有重要变更的任务
                summary.append({
                    'task_id': task_data['task_id'],
                    'task_title': task_data['title'],
                    'changes_count': len(task_data['major_changes']),
                    'last_change': task_data['last_modified'],
                    'recent_changes': task_data['major_changes'][-3:]  # 最近3个变更
                })
        
        return summary

class TaskHistoryFilter:
    """任务历史过滤器"""
    
    def __init__(self, privacy_boundary: PrivacyBoundary):
        self.privacy_boundary = privacy_boundary
    
    def filter_history_for_user(
        self, 
        user_role: PermissionLevel, 
        full_history: List[Dict],
        task_creator_id: int,
        current_user_id: int
    ) -> List[Dict]:
        """为用户过滤合适的历史记录"""
        
        visibility = self.privacy_boundary.get_history_visibility(user_role)
        
        if visibility == HistoryVisibility.FULL:
            # 所有者可以看到完整历史
            return full_history
            
        elif visibility == HistoryVisibility.ANONYMIZED:
            # 管理员看到匿名历史
            return self.privacy_boundary.get_anonymized_history(full_history)
            
        elif visibility == HistoryVisibility.SUMMARY:
            # 编辑者和查看者看到概要
            return self.privacy_boundary.get_summary_history(full_history)
            
        else:  # HistoryVisibility.NONE
            # 评论者看不到历史
            return []
    
    def should_hide_operator_identity(
        self, 
        user_role: PermissionLevel, 
        operator_id: int,
        current_user_id: int,
        task_creator_id: int
    ) -> bool:
        """判断是否应该隐藏操作者身份"""
        
        # 自己的操作总是可见
        if operator_id == current_user_id:
            return False
            
        # 任务创建者的操作对管理员可见
        if user_role == PermissionLevel.ADMIN and operator_id == task_creator_id:
            return False
            
        # 其他情况下根据权限等级决定
        return not self.privacy_boundary.can_view_full_history(user_role)

# 使用示例
def demonstrate_privacy_control():
    """演示隐私控制机制"""
    
    privacy = PrivacyBoundary()
    filter_service = TaskHistoryFilter(privacy)
    
    # 模拟历史记录
    sample_history = [
        {
            'id': 1,
            'task_id': 100,
            'task_title': '项目规划',
            'field_name': 'title',
            'old_value': '初步规划',
            'new_value': '详细项目规划',
            'operator': '张三',
            'operator_id': 1,
            'timestamp': '2024-01-01T10:00:00',
            'change_type': 'update'
        },
        {
            'id': 2,
            'task_id': 100,
            'task_title': '项目规划',
            'field_name': 'completed',
            'old_value': 'False',
            'new_value': 'True',
            'operator': '李四',
            'operator_id': 2,
            'timestamp': '2024-01-01T15:30:00',
            'change_type': 'update'
        }
    ]
    
    print("=== 隐私边界控制演示 ===\n")
    
    # 不同角色的可见性
    roles = [
        PermissionLevel.OWNER,
        PermissionLevel.ADMIN,
        PermissionLevel.EDITOR,
        PermissionLevel.VIEWER,
        PermissionLevel.COMMENTER
    ]
    
    for role in roles:
        print(f"{role.value.upper()} 权限:")
        visibility = privacy.get_history_visibility(role)
        print(f"  历史可见性: {visibility.value}")
        
        filtered = filter_service.filter_history_for_user(
            role, sample_history, task_creator_id=1, current_user_id=3
        )
        
        print(f"  可见记录数: {len(filtered)}")
        if filtered:
            print("  示例记录:")
            for record in filtered[:1]:  # 只显示第一条
                print(f"    {record}")
        print()

if __name__ == "__main__":
    demonstrate_privacy_control()