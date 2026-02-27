from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Set
import json
from datetime import datetime
import asyncio
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas import schemas
from app.models import models

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}  # user_id -> connections
        self.room_connections: Dict[str, Set[int]] = {}  # room_id -> user_ids
        self.user_rooms: Dict[int, Set[str]] = {}  # user_id -> room_ids
        self.connection_info: Dict[WebSocket, dict] = {}  # connection -> info

    async def connect(self, websocket: WebSocket, user_id: int, rooms: List[str] = None):
        await websocket.accept()
        
        # 记录连接信息
        self.connection_info[websocket] = {
            'user_id': user_id,
            'rooms': set(rooms or []),
            'connected_at': datetime.utcnow()
        }
        
        # 添加到用户连接
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # 添加到房间
        if rooms:
            for room_id in rooms:
                if room_id not in self.room_connections:
                    self.room_connections[room_id] = set()
                self.room_connections[room_id].add(user_id)
                
                if user_id not in self.user_rooms:
                    self.user_rooms[user_id] = set()
                self.user_rooms[user_id].add(room_id)
        
        print(f"用户 {user_id} 已连接，当前在线用户: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket not in self.connection_info:
            return
            
        info = self.connection_info[websocket]
        user_id = info['user_id']
        rooms = info['rooms']
        
        # 从用户连接中移除
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # 从房间中移除
        for room_id in rooms:
            if room_id in self.room_connections and user_id in self.room_connections[room_id]:
                self.room_connections[room_id].remove(user_id)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
            
            if user_id in self.user_rooms and room_id in self.user_rooms[user_id]:
                self.user_rooms[user_id].remove(room_id)
                if not self.user_rooms[user_id]:
                    del self.user_rooms[user_id]
        
        # 清理连接信息
        del self.connection_info[websocket]
        
        print(f"用户 {user_id} 已断开连接，当前在线用户: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            message_str = json.dumps(message, ensure_ascii=False)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    print(f"发送个人消息失败: {e}")

    async def send_room_message(self, message: dict, room_id: str):
        if room_id in self.room_connections:
            message_str = json.dumps(message, ensure_ascii=False)
            user_ids = self.room_connections[room_id]
            for user_id in user_ids:
                await self.send_personal_message(message, user_id)

    async def broadcast(self, message: dict):
        message_str = json.dumps(message, ensure_ascii=False)
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    print(f"广播消息失败: {e}")

    async def join_room(self, websocket: WebSocket, room_id: str):
        if websocket not in self.connection_info:
            return False
            
        info = self.connection_info[websocket]
        user_id = info['user_id']
        
        # 添加到房间
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(user_id)
        
        # 添加到用户房间列表
        if user_id not in self.user_rooms:
            self.user_rooms[user_id] = set()
        self.user_rooms[user_id].add(room_id)
        
        # 更新连接信息
        info['rooms'].add(room_id)
        
        return True

    async def leave_room(self, websocket: WebSocket, room_id: str):
        if websocket not in self.connection_info:
            return False
            
        info = self.connection_info[websocket]
        user_id = info['user_id']
        
        # 从房间移除
        if room_id in self.room_connections and user_id in self.room_connections[room_id]:
            self.room_connections[room_id].remove(user_id)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
        
        # 从用户房间列表移除
        if user_id in self.user_rooms and room_id in self.user_rooms[user_id]:
            self.user_rooms[user_id].remove(room_id)
            if not self.user_rooms[user_id]:
                del self.user_rooms[user_id]
        
        # 更新连接信息
        info['rooms'].discard(room_id)
        
        return True

    def get_user_count(self) -> int:
        return len(self.active_connections)
    
    def get_room_users(self, room_id: str) -> Set[int]:
        return self.room_connections.get(room_id, set())
    
    def get_user_rooms(self, user_id: int) -> Set[str]:
        return self.user_rooms.get(user_id, set())

manager = ConnectionManager()

@router.websocket("/sync")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    rooms: str = Query(None),
    db: Session = Depends(get_db)
):
    # 验证JWT令牌
    try:
        user_id = get_current_user(token, db).id
    except Exception as e:
        await websocket.close(code=4001, reason="认证失败")
        return
    
    # 解析房间列表
    room_list = rooms.split(',') if rooms else []
    
    await manager.connect(websocket, user_id, room_list)
    
    try:
        # 发送连接确认消息
        await manager.send_personal_message({
            "type": "connection_confirmed",
            "user_id": user_id,
            "rooms": room_list,
            "online_users": manager.get_user_count(),
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 处理不同类型的消息
            message_type = message_data.get("type", "unknown")
            
            if message_type == "sync_request":
                # 同步请求 - 广播给房间内的其他用户
                room_id = message_data.get("room_id")
                if room_id:
                    await manager.send_room_message({
                        "type": "sync_update",
                        "sender_id": user_id,
                        "data": message_data.get("data", {}),
                        "timestamp": datetime.utcnow().isoformat()
                    }, room_id)
                
            elif message_type == "join_room":
                # 加入房间
                room_id = message_data.get("room_id")
                if room_id:
                    success = await manager.join_room(websocket, room_id)
                    await manager.send_personal_message({
                        "type": "room_joined",
                        "room_id": room_id,
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                
            elif message_type == "leave_room":
                # 离开房间
                room_id = message_data.get("room_id")
                if room_id:
                    success = await manager.leave_room(websocket, room_id)
                    await manager.send_personal_message({
                        "type": "room_left",
                        "room_id": room_id,
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                
            elif message_type == "heartbeat":
                # 心跳消息
                await manager.send_personal_message({
                    "type": "heartbeat_ack",
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # 通知房间内其他用户有人离开
        for room_id in manager.get_user_rooms(user_id):
            await manager.send_room_message({
                "type": "user_left_room",
                "user_id": user_id,
                "room_id": room_id,
                "timestamp": datetime.utcnow().isoformat()
            }, room_id)
    
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

@router.post("/send-message")
async def send_message(
    message: schemas.WebSocketMessage,
    current_user: models.User = Depends(get_current_user)
):
    """发送WebSocket消息"""
    message_dict = message.dict()
    message_dict["timestamp"] = datetime.utcnow().isoformat()
    
    await manager.send_personal_message(
        json.dumps(message_dict),
        current_user.id
    )
    
    return {"status": "message_sent"}

@router.get("/stats")
async def get_websocket_stats(
    current_user: models.User = Depends(get_current_user)
):
    """获取WebSocket连接统计信息"""
    return {
        "online_users": manager.get_user_count(),
        "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
        "rooms": [
            {
                "room_id": room_id,
                "user_count": len(users)
            }
            for room_id, users in manager.room_connections.items()
        ]
    }

@router.post("/broadcast")
async def broadcast_message(
    message: schemas.WebSocketMessage,
    current_user: models.User = Depends(get_current_user)
):
    """广播消息给所有连接的用户"""
    message_dict = message.dict()
    message_dict["timestamp"] = datetime.utcnow().isoformat()
    message_dict["sender_id"] = current_user.id
    
    await manager.broadcast(message_dict)
    return {"status": "broadcast_sent", "recipients": manager.get_user_count()}

@router.post("/room/{room_id}/send")
async def send_to_room(
    room_id: str,
    message: schemas.WebSocketMessage,
    current_user: models.User = Depends(get_current_user)
):
    """发送消息到指定房间"""
    message_dict = message.dict()
    message_dict["timestamp"] = datetime.utcnow().isoformat()
    message_dict["sender_id"] = current_user.id
    message_dict["room_id"] = room_id
    
    await manager.send_room_message(message_dict, room_id)
    return {
        "status": "message_sent", 
        "room_id": room_id, 
        "recipients": len(manager.get_room_users(room_id))
    }