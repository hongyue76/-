from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas import schemas
from app.models import models
from app.utils.timestamp_service import get_consistent_timestamp

router = APIRouter(tags=["离线同步"])


@router.post("/sync", response_model=schemas.SyncResponse)
def sync_offline_operations(
    sync_request: schemas.SyncRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    离线数据同步接口
    处理客户端上传的离线操作并返回服务器端更新
    """
    try:
        # 1. 处理客户端上传的离线操作
        conflicts = []
        processed_operations = []
        
        for op_data in sync_request.pending_operations:
            # 获取服务器时间戳
            timestamp_info = get_consistent_timestamp()
            
            # 创建操作记录
            operation = models.OfflineOperation(
                user_id=current_user.id,
                todo_id=op_data.todo_id,
                operation_type=op_data.operation_type,
                field_name=op_data.field_name,
                old_value=op_data.old_value,
                new_value=op_data.new_value,
                client_timestamp=op_data.timestamp if hasattr(op_data, 'timestamp') else None,
                server_timestamp=datetime.utcnow(),
                logical_timestamp=timestamp_info["logical_timestamp"],
                sequence_id=str(uuid.uuid4()),
                device_id=sync_request.device_id,
                sync_status="pending"
            )
            db.add(operation)
            processed_operations.append(operation)
        
        db.commit()
        
        # 2. 应用操作并检测冲突
        for operation in processed_operations:
            conflict = apply_operation(db, operation, current_user.id)
            if conflict:
                conflicts.append(conflict)
                operation.sync_status = "conflicted"
            else:
                operation.sync_status = "synced"
        
        db.commit()
        
        # 3. 获取服务器端更新
        server_updates = get_server_updates(
            db, 
            current_user.id, 
            sync_request.last_sync_time
        )
        
        # 4. 更新同步时间戳
        update_last_sync_time(db, current_user.id, sync_request.device_id)
        
        return schemas.SyncResponse(
            server_updates=server_updates,
            conflicts=conflicts,
            sync_timestamp=datetime.utcnow(),
            has_more=False
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步失败: {str(e)}"
        )

@router.get("/operations/pending", response_model=List[schemas.OfflineOperationResponse])
def get_pending_operations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取用户的待处理操作"""
    operations = db.query(models.OfflineOperation).filter(
        models.OfflineOperation.user_id == current_user.id,
        models.OfflineOperation.sync_status == "pending"
    ).order_by(models.OfflineOperation.timestamp).all()
    
    return operations

@router.post("/resolve-conflict")
def resolve_conflict(
    resolution: schemas.ConflictResolution,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """解决同步冲突"""
    operation = db.query(models.OfflineOperation).filter(
        models.OfflineOperation.id == resolution.operation_id,
        models.OfflineOperation.user_id == current_user.id
    ).first()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="操作记录不存在"
        )
    
    # 根据解决策略处理冲突
    if resolution.resolution == "accept_client":
        # 接受客户端更改
        apply_operation_force(db, operation)
    elif resolution.resolution == "accept_server":
        # 接受服务端数据，忽略客户端更改
        operation.sync_status = "resolved"
    elif resolution.resolution == "merge":
        # 合并更改
        merge_changes(db, operation, resolution.merged_data)
    
    db.commit()
    return {"message": "冲突已解决"}

def apply_operation(db: Session, operation: models.OfflineOperation, user_id: int) -> dict:
    """应用离线操作，基于服务器时间戳检测冲突"""
    todo = db.query(models.Todo).filter(
        models.Todo.id == operation.todo_id,
        models.Todo.user_id == user_id
    ).first()
    
    if not todo:
        return {"error": "任务不存在", "operation_id": operation.id}
    
    # 基于服务器时间戳的冲突检测
    conflict_detected = False
    if operation.operation_type == "UPDATE":
        current_value = getattr(todo, operation.field_name, None)
        
        # 使用服务器时间戳进行精确的时序判断
        if (hasattr(todo, 'updated_at') and 
            todo.updated_at and operation.server_timestamp):
            # 如果任务更新时间晚于操作记录时间，说明有并发修改
            if todo.updated_at > operation.server_timestamp.replace(tzinfo=None):
                conflict_detected = True
        
        # 传统值比较作为补充
        elif (current_value is not None and 
              str(current_value) != str(operation.old_value) and
              operation.old_value is not None):
            conflict_detected = True
        
        if conflict_detected:
            # 记录冲突信息
            todo.conflict_status = "detected"
            print(f"检测到冲突: 任务{todo.id}的{operation.field_name}字段")
            print(f"服务器当前值: {current_value}")
            print(f"客户端原始值: {operation.old_value}")
            print(f"客户端新值: {operation.new_value}")
            print(f"服务器时间戳: {operation.server_timestamp}")
            print(f"任务更新时间: {todo.updated_at}")
        
        # 应用更新（基于服务器时间戳的LWW策略）
        if hasattr(todo, operation.field_name):
            setattr(todo, operation.field_name, operation.new_value)
        
        # 更新元数据
        if hasattr(todo, 'version'):
            todo.version += 1
        todo.updated_at = datetime.utcnow()
        
        # 如果有冲突，返回冲突详情供客户端处理
        if conflict_detected:
            return {
                "conflict": True,
                "field": operation.field_name,
                "server_value": current_value,
                "client_old_value": operation.old_value,
                "client_new_value": operation.new_value,
                "server_timestamp": operation.server_timestamp.isoformat() if operation.server_timestamp else None,
                "task_updated_at": todo.updated_at.isoformat() if todo.updated_at else None,
                "operation_id": operation.id
            }
    
    elif operation.operation_type == "DELETE":
        db.delete(todo)
    
    return None

def apply_operation_force(db: Session, operation: models.OfflineOperation):
    """强制应用操作（用于冲突解决）"""
    todo = db.query(models.Todo).filter(
        models.Todo.id == operation.todo_id
    ).first()
    
    if todo and operation.operation_type == "UPDATE":
        if hasattr(todo, operation.field_name):
            setattr(todo, operation.field_name, operation.new_value)
        if hasattr(todo, 'version'):
            todo.version += 1
        todo.updated_at = datetime.utcnow()
    
    operation.sync_status = "resolved"

def merge_changes(db: Session, operation: models.OfflineOperation, merged_data: dict):
    """合并更改"""
    todo = db.query(models.Todo).filter(
        models.Todo.id == operation.todo_id
    ).first()
    
    if todo and merged_data:
        for field, value in merged_data.items():
            if hasattr(todo, field):
                setattr(todo, field, value)
        if hasattr(todo, 'version'):
            todo.version += 1
        todo.updated_at = datetime.utcnow()
    
    operation.sync_status = "resolved"

def get_server_updates(db: Session, user_id: int, last_sync_time: datetime) -> List[schemas.TodoResponse]:
    """获取服务器端更新"""
    query = db.query(models.Todo).filter(
        models.Todo.user_id == user_id
    )
    
    if last_sync_time:
        query = query.filter(models.Todo.updated_at > last_sync_time)
    
    todos = query.all()
    
    # 转换为响应模型
    return [schemas.TodoResponse.model_validate(todo) for todo in todos]

def update_last_sync_time(db: Session, user_id: int, device_id: str):
    """更新最后同步时间"""
    # 这里可以扩展为记录每个设备的同步时间
    pass