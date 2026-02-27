"""
实时协作状态服务
提供轻量级的用户感知优化
"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class UserPresence:
    """用户在线状态"""
    user_id: int
    username: str
    status: str  # online, idle, offline
    last_active: datetime
    current_task: Optional[int] = None
    current_field: Optional[str] = None

@dataclass
class EditingIndicator:
    """编辑指示器"""
    task_id: int
    field_name: str
    user_id: int
    username: str
    start_time: datetime
    is_typing: bool = False

class CollaborationPresence:
    """协作状态管理器"""
    
    def __init__(self):
        self.active_users: Dict[int, UserPresence] = {}
        self.editing_indicators: Dict[str, EditingIndicator] = {}  # key: task_field_user
        self.presence_callbacks = []
        self.editing_callbacks = []
    
    def user_join(self, user_id: int, username: str):
        """用户加入清单"""
        self.active_users[user_id] = UserPresence(
            user_id=user_id,
            username=username,
            status='online',
            last_active=datetime.now()
        )
        self._notify_presence_change()
    
    def user_leave(self, user_id: int):
        """用户离开清单"""
        if user_id in self.active_users:
            del self.active_users[user_id]
            # 清理该用户的所有编辑状态
            keys_to_remove = [
                key for key in self.editing_indicators 
                if self.editing_indicators[key].user_id == user_id
            ]
            for key in keys_to_remove:
                del self.editing_indicators[key]
            
            self._notify_presence_change()
            self._notify_editing_change()
    
    def start_editing(self, user_id: int, task_id: int, field_name: str):
        """开始编辑"""
        key = f"{task_id}_{field_name}_{user_id}"
        username = self.active_users.get(user_id, {}).username or f"用户{user_id}"
        
        self.editing_indicators[key] = EditingIndicator(
            task_id=task_id,
            field_name=field_name,
            user_id=user_id,
            username=username,
            start_time=datetime.now(),
            is_typing=True
        )
        
        # 更新用户当前状态
        if user_id in self.active_users:
            self.active_users[user_id].current_task = task_id
            self.active_users[user_id].current_field = field_name
            self.active_users[user_id].last_active = datetime.now()
        
        self._notify_editing_change()
    
    def stop_editing(self, user_id: int, task_id: int, field_name: str):
        """停止编辑"""
        key = f"{task_id}_{field_name}_{user_id}"
        if key in self.editing_indicators:
            del self.editing_indicators[key]
        
        # 清理用户状态
        if user_id in self.active_users:
            if (self.active_users[user_id].current_task == task_id and 
                self.active_users[user_id].current_field == field_name):
                self.active_users[user_id].current_task = None
                self.active_users[user_id].current_field = None
        
        self._notify_editing_change()
    
    def update_typing_status(self, user_id: int, task_id: int, field_name: str, is_typing: bool):
        """更新打字状态"""
        key = f"{task_id}_{field_name}_{user_id}"
        if key in self.editing_indicators:
            self.editing_indicators[key].is_typing = is_typing
            self._notify_editing_change()
    
    def get_active_editors(self, task_id: int, field_name: str = None) -> List[EditingIndicator]:
        """获取当前编辑者"""
        editors = []
        for indicator in self.editing_indicators.values():
            if indicator.task_id == task_id:
                if field_name is None or indicator.field_name == field_name:
                    editors.append(indicator)
        return editors
    
    def get_online_users(self) -> List[UserPresence]:
        """获取在线用户列表"""
        return list(self.active_users.values())
    
    def add_presence_listener(self, callback):
        """添加状态变化监听器"""
        self.presence_callbacks.append(callback)
    
    def add_editing_listener(self, callback):
        """添加编辑状态监听器"""
        self.editing_callbacks.append(callback)
    
    def _notify_presence_change(self):
        """通知状态变化"""
        data = {
            'type': 'presence_change',
            'users': [self._serialize_user(u) for u in self.active_users.values()],
            'timestamp': datetime.now().isoformat()
        }
        
        for callback in self.presence_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Presence callback error: {e}")
    
    def _notify_editing_change(self):
        """通知编辑状态变化"""
        data = {
            'type': 'editing_change',
            'indicators': [self._serialize_indicator(i) for i in self.editing_indicators.values()],
            'timestamp': datetime.now().isoformat()
        }
        
        for callback in self.editing_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Editing callback error: {e}")
    
    def _serialize_user(self, user: UserPresence) -> dict:
        """序列化用户信息"""
        return {
            'user_id': user.user_id,
            'username': user.username,
            'status': user.status,
            'last_active': user.last_active.isoformat(),
            'current_task': user.current_task,
            'current_field': user.current_field
        }
    
    def _serialize_indicator(self, indicator: EditingIndicator) -> dict:
        """序列化编辑指示器"""
        return {
            'task_id': indicator.task_id,
            'field_name': indicator.field_name,
            'user_id': indicator.user_id,
            'username': indicator.username,
            'start_time': indicator.start_time.isoformat(),
            'is_typing': indicator.is_typing
        }

# 全局实例
collaboration_presence = CollaborationPresence()

class PresenceWebSocketHandler:
    """WebSocket状态处理"""
    
    def __init__(self):
        self.connections = {}
        collaboration_presence.add_presence_listener(self.broadcast_presence)
        collaboration_presence.add_editing_listener(self.broadcast_editing)
    
    def add_connection(self, user_id: int, websocket):
        """添加WebSocket连接"""
        self.connections[user_id] = websocket
        collaboration_presence.user_join(user_id, f"用户{user_id}")
    
    def remove_connection(self, user_id: int):
        """移除WebSocket连接"""
        if user_id in self.connections:
            del self.connections[user_id]
            collaboration_presence.user_leave(user_id)
    
    async def broadcast_presence(self, data: dict):
        """广播状态变化"""
        message = json.dumps(data)
        for user_id, websocket in self.connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Failed to send presence to user {user_id}: {e}")
                self.remove_connection(user_id)
    
    async def broadcast_editing(self, data: dict):
        """广播编辑状态"""
        message = json.dumps(data)
        for user_id, websocket in self.connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Failed to send editing to user {user_id}: {e}")
                self.remove_connection(user_id)
    
    async def handle_message(self, user_id: int, message: str):
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'start_editing':
                collaboration_presence.start_editing(
                    user_id, 
                    data['task_id'], 
                    data['field_name']
                )
            
            elif message_type == 'stop_editing':
                collaboration_presence.stop_editing(
                    user_id, 
                    data['task_id'], 
                    data['field_name']
                )
            
            elif message_type == 'typing':
                collaboration_presence.update_typing_status(
                    user_id,
                    data['task_id'],
                    data['field_name'],
                    data['is_typing']
                )
                
        except json.JSONDecodeError:
            print(f"Invalid JSON from user {user_id}")
        except Exception as e:
            print(f"Error handling message from user {user_id}: {e}")

# 使用示例
def demonstrate_presence_system():
    """演示状态系统"""
    print("=== 实时协作状态系统演示 ===\n")
    
    # 模拟用户活动
    collaboration_presence.user_join(1, "张三")
    collaboration_presence.user_join(2, "李四")
    
    print("1. 用户上线:")
    users = collaboration_presence.get_online_users()
    for user in users:
        print(f"   - {user.username} ({user.status})")
    
    print("\n2. 开始编辑:")
    collaboration_presence.start_editing(1, 100, "title")
    collaboration_presence.start_editing(2, 100, "description")
    
    editors = collaboration_presence.get_active_editors(100)
    for editor in editors:
        print(f"   - {editor.username} 正在编辑 {editor.field_name}")
    
    print("\n3. 更新打字状态:")
    collaboration_presence.update_typing_status(1, 100, "title", True)
    editors = collaboration_presence.get_active_editors(100, "title")
    for editor in editors:
        status = "正在输入" if editor.is_typing else "暂停输入"
        print(f"   - {editor.username} {status}")
    
    print("\n4. 停止编辑:")
    collaboration_presence.stop_editing(1, 100, "title")
    remaining_editors = collaboration_presence.get_active_editors(100)
    print(f"   剩余编辑者: {len(remaining_editors)} 人")
    
    print("\n5. 用户下线:")
    collaboration_presence.user_leave(2)
    final_users = collaboration_presence.get_online_users()
    print(f"   在线用户: {len(final_users)} 人")

if __name__ == "__main__":
    demonstrate_presence_system()