"""
协作状态WebSocket路由
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
from typing import Dict
from app.utils.presence_service import PresenceWebSocketHandler, collaboration_presence

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# 全局WebSocket处理器
ws_handler = PresenceWebSocketHandler()

@router.websocket("/collaboration/{list_id}")
async def collaboration_websocket(websocket: WebSocket, list_id: int):
    """协作状态WebSocket连接"""
    await websocket.accept()
    
    # 获取用户信息（实际应用中应从token解析）
    try:
        # 简化实现，实际应验证JWT token
        user_id = int(websocket.query_params.get("user_id", 0))
        if not user_id:
            await websocket.close(code=4000, reason="Missing user_id")
            return
    except ValueError:
        await websocket.close(code=4000, reason="Invalid user_id")
        return
    
    # 添加连接
    ws_handler.add_connection(user_id, websocket)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            await ws_handler.handle_message(user_id, data)
            
    except WebSocketDisconnect:
        # 用户断开连接
        ws_handler.remove_connection(user_id)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        ws_handler.remove_connection(user_id)

@router.get("/collaboration/{list_id}/presence")
async def get_collaboration_presence(list_id: int):
    """获取当前协作状态"""
    return {
        "online_users": [
            {
                "user_id": user.user_id,
                "username": user.username,
                "status": user.status,
                "last_active": user.last_active.isoformat(),
                "current_task": user.current_task,
                "current_field": user.current_field
            }
            for user in collaboration_presence.get_online_users()
        ],
        "active_editors": [
            {
                "task_id": indicator.task_id,
                "field_name": indicator.field_name,
                "user_id": indicator.user_id,
                "username": indicator.username,
                "start_time": indicator.start_time.isoformat(),
                "is_typing": indicator.is_typing
            }
            for indicator in collaboration_presence.get_active_editors(None)
        ]
    }

@router.post("/collaboration/{list_id}/notifications")
async def send_field_notification(list_id: int, notification: dict):
    """发送字段级通知"""
    # 这里可以添加通知逻辑
    # 例如：某用户开始/停止编辑某个字段
    
    message = {
        "type": "field_notification",
        "username": notification.get("username", "用户"),
        "action": notification.get("action", "正在编辑"),
        "field": notification.get("field", "字段"),
        "task_id": notification.get("task_id"),
        "timestamp": notification.get("timestamp")
    }
    
    # 广播通知（简化实现）
    # 实际应用中应该通过WebSocket广播给相关用户
    
    return {"message": "通知已发送"}

# 测试页面
@router.get("/collaboration/demo")
async def collaboration_demo():
    """协作功能演示页面"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>协作状态演示</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            .user-list { background: #f5f7fa; padding: 15px; border-radius: 6px; }
            .user-item { margin: 10px 0; padding: 8px; background: white; border-radius: 4px; }
            .indicator { background: #e6f7ff; padding: 15px; border-radius: 6px; margin: 10px 0; }
            button { padding: 10px 15px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #409eff; color: white; }
            .btn-success { background: #67c23a; color: white; }
            .btn-warning { background: #e6a23c; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>实时协作状态演示</h1>
            
            <div class="section">
                <h2>连接控制</h2>
                <button class="btn-primary" onclick="connectWebSocket()">连接WebSocket</button>
                <button class="btn-warning" onclick="disconnectWebSocket()">断开连接</button>
            </div>
            
            <div class="section">
                <h2>在线用户</h2>
                <div id="userList" class="user-list">
                    <p>等待连接...</p>
                </div>
            </div>
            
            <div class="section">
                <h2>编辑状态</h2>
                <div id="editingIndicators">
                    <p>暂无编辑活动</p>
                </div>
            </div>
            
            <div class="section">
                <h2>模拟操作</h2>
                <button class="btn-success" onclick="startEditing(1, 'title')">开始编辑任务1标题</button>
                <button class="btn-warning" onclick="stopEditing(1, 'title')">停止编辑任务1标题</button>
                <br><br>
                <button class="btn-success" onclick="startEditing(2, 'description')">开始编辑任务2描述</button>
                <button class="btn-warning" onclick="stopEditing(2, 'description')">停止编辑任务2描述</button>
            </div>
        </div>

        <script>
            let ws = null;
            let userId = Math.floor(Math.random() * 1000) + 1;
            
            function connectWebSocket() {
                if (ws) {
                    console.log('已连接');
                    return;
                }
                
                const wsUrl = `ws://localhost:8000/api/ws/collaboration/1?user_id=${userId}`;
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    console.log('WebSocket连接已建立');
                    document.querySelector('.section:first-child').innerHTML += 
                        `<p style="color: green;">已连接 (用户ID: ${userId})</p>`;
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    console.log('收到消息:', data);
                    
                    if (data.type === 'presence_change') {
                        updateUserList(data.users);
                    } else if (data.type === 'editing_change') {
                        updateEditingIndicators(data.indicators);
                    }
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket连接已关闭');
                    ws = null;
                    document.querySelector('.section:first-child').innerHTML = 
                        '<h2>连接控制</h2>' +
                        '<button class="btn-primary" onclick="connectWebSocket()">连接WebSocket</button>' +
                        '<button class="btn-warning" onclick="disconnectWebSocket()">断开连接</button>' +
                        '<p style="color: red;">连接已断开</p>';
                };
            }
            
            function disconnectWebSocket() {
                if (ws) {
                    ws.close();
                }
            }
            
            function updateUserList(users) {
                const userList = document.getElementById('userList');
                if (users.length === 0) {
                    userList.innerHTML = '<p>暂无在线用户</p>';
                    return;
                }
                
                userList.innerHTML = users.map(user => `
                    <div class="user-item">
                        <strong>${user.username}</strong> 
                        (${user.status})
                        ${user.current_task ? `<span style="color: orange;">正在编辑任务${user.current_task}</span>` : ''}
                    </div>
                `).join('');
            }
            
            function updateEditingIndicators(indicators) {
                const container = document.getElementById('editingIndicators');
                if (indicators.length === 0) {
                    container.innerHTML = '<p>暂无编辑活动</p>';
                    return;
                }
                
                container.innerHTML = indicators.map(indicator => `
                    <div class="indicator">
                        <strong>${indicator.username}</strong> 正在编辑任务${indicator.task_id}的${indicator.field_name}
                        ${indicator.is_typing ? '<span style="color: blue;"> (输入中...)</span>' : ''}
                    </div>
                `).join('');
            }
            
            function startEditing(taskId, fieldName) {
                if (!ws) {
                    alert('请先连接WebSocket');
                    return;
                }
                
                ws.send(JSON.stringify({
                    type: 'start_editing',
                    task_id: taskId,
                    field_name: fieldName
                }));
            }
            
            function stopEditing(taskId, fieldName) {
                if (!ws) {
                    alert('请先连接WebSocket');
                    return;
                }
                
                ws.send(JSON.stringify({
                    type: 'stop_editing',
                    task_id: taskId,
                    field_name: fieldName
                }));
            }
        </script>
    </body>
    </html>
    """)