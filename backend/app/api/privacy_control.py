"""
共享清单隐私控制API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import models
from app.schemas import schemas
from app.api.auth import get_current_user
from app.utils.privacy_control import (
    PrivacyBoundary, 
    TaskHistoryFilter, 
    PermissionLevel, 
    HistoryVisibility
)

router = APIRouter(prefix="/privacy", tags=["隐私控制"])

# 初始化隐私控制服务
privacy_boundary = PrivacyBoundary()
history_filter = TaskHistoryFilter(privacy_boundary)

@router.get("/lists/{list_id}/permissions")
def get_list_permissions(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取共享清单的权限设置"""
    
    # 验证用户是否有查看权限
    shared_list = db.query(models.SharedList).filter(
        models.SharedList.id == list_id
    ).first()
    
    if not shared_list:
        raise HTTPException(status_code=404, detail="清单不存在")
    
    # 检查用户是否是清单成员
    member = db.query(models.SharedListMember).filter(
        models.SharedListMember.list_id == list_id,
        models.SharedListMember.user_id == current_user.id
    ).first()
    
    if not member and shared_list.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此清单")
    
    # 获取所有成员权限
    members = db.query(models.SharedListMember).filter(
        models.SharedListMember.list_id == list_id
    ).all()
    
    # 获取用户自己的权限等级
    user_permission = PermissionLevel.OWNER if shared_list.owner_id == current_user.id else member.permission
    
    return {
        "list_id": list_id,
        "user_permission": user_permission.value,
        "members": [
            {
                "user_id": m.user_id,
                "username": m.user.username,
                "permission": m.permission,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None
            }
            for m in members
        ],
        "privacy_settings": {
            "default_permission": shared_list.default_permission,
            "history_visibility": shared_list.history_visibility,
            "anonymize_operators": shared_list.anonymize_operators
        }
    }

@router.put("/lists/{list_id}/permissions")
def update_list_permissions(
    list_id: int,
    permissions_update: schemas.ListPermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """更新共享清单权限设置"""
    
    # 验证用户是否是所有者
    shared_list = db.query(models.SharedList).filter(
        models.SharedList.id == list_id,
        models.SharedList.owner_id == current_user.id
    ).first()
    
    if not shared_list:
        raise HTTPException(status_code=403, detail="只有清单所有者可以修改权限")
    
    # 更新清单隐私设置
    if permissions_update.default_permission:
        shared_list.default_permission = permissions_update.default_permission
    
    if permissions_update.history_visibility:
        shared_list.history_visibility = permissions_update.history_visibility
    
    if permissions_update.anonymize_operators is not None:
        shared_list.anonymize_operators = permissions_update.anonymize_operators
    
    db.commit()
    
    return {"message": "权限设置更新成功"}

@router.put("/lists/{list_id}/members/{member_id}/permission")
def update_member_permission(
    list_id: int,
    member_id: int,
    permission_update: schemas.MemberPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """更新成员权限"""
    
    # 验证操作权限
    shared_list = db.query(models.SharedList).filter(
        models.SharedList.id == list_id
    ).first()
    
    if not shared_list:
        raise HTTPException(status_code=404, detail="清单不存在")
    
    # 只有所有者和管理员可以修改成员权限
    if shared_list.owner_id != current_user.id:
        member = db.query(models.SharedListMember).filter(
            models.SharedListMember.list_id == list_id,
            models.SharedListMember.user_id == current_user.id
        ).first()
        
        if not member or member.permission not in ['admin']:
            raise HTTPException(status_code=403, detail="无权修改成员权限")
    
    # 不能修改所有者权限
    if member_id == shared_list.owner_id:
        raise HTTPException(status_code=400, detail="不能修改清单所有者的权限")
    
    # 更新成员权限
    target_member = db.query(models.SharedListMember).filter(
        models.SharedListMember.list_id == list_id,
        models.SharedListMember.user_id == member_id
    ).first()
    
    if not target_member:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    target_member.permission = permission_update.permission
    db.commit()
    
    return {"message": "成员权限更新成功"}

@router.get("/lists/{list_id}/tasks/{task_id}/history")
def get_filtered_task_history(
    list_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取过滤后的历史记录"""
    
    # 验证访问权限
    shared_list = db.query(models.SharedList).filter(
        models.SharedList.id == list_id
    ).first()
    
    if not shared_list:
        raise HTTPException(status_code=404, detail="清单不存在")
    
    # 检查用户权限
    if shared_list.owner_id == current_user.id:
        user_permission = PermissionLevel.OWNER
    else:
        member = db.query(models.SharedListMember).filter(
            models.SharedListMember.list_id == list_id,
            models.SharedListMember.user_id == current_user.id
        ).first()
        
        if not member:
            raise HTTPException(status_code=403, detail="无权访问此清单")
        
        user_permission = PermissionLevel(member.permission)
    
    # 获取完整历史记录
    # 这里应该从操作记录表查询相关任务的所有历史操作
    full_history = get_task_full_history(db, task_id, list_id)
    
    # 根据权限过滤历史记录
    filtered_history = history_filter.filter_history_for_user(
        user_permission,
        full_history,
        task_creator_id=shared_list.owner_id,
        current_user_id=current_user.id
    )
    
    # 检查是否需要匿名化操作者身份
    should_anonymize = (
        shared_list.anonymize_operators and 
        not privacy_boundary.can_view_full_history(user_permission)
    )
    
    if should_anonymize:
        filtered_history = anonymize_operators(filtered_history)
    
    return {
        "task_id": task_id,
        "permission_level": user_permission.value,
        "history_visibility": privacy_boundary.get_history_visibility(user_permission).value,
        "records": filtered_history,
        "total_records": len(filtered_history)
    }

def get_task_full_history(db: Session, task_id: int, list_id: int) -> List[dict]:
    """获取任务的完整历史记录"""
    # 这里应该查询操作记录表获取完整历史
    # 简化实现，实际应该关联查询
    return [
        {
            'id': 1,
            'task_id': task_id,
            'field_name': 'title',
            'old_value': '旧标题',
            'new_value': '新标题',
            'operator': '操作者姓名',
            'operator_id': 123,
            'timestamp': '2024-01-01T10:00:00',
            'change_type': 'update'
        }
    ]

def anonymize_operators(history_records: List[dict]) -> List[dict]:
    """匿名化操作者身份"""
    for record in history_records:
        if 'operator' in record:
            record['operator'] = '协作者'
        if 'operator_id' in record:
            del record['operator_id']
    return history_records

# Schema定义
class ListPermissionsUpdate(BaseModel):
    default_permission: Optional[str] = None
    history_visibility: Optional[str] = None
    anonymize_operators: Optional[bool] = None

class MemberPermissionUpdate(BaseModel):
    permission: str