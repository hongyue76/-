from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.crud import progress as progress_crud
from app.schemas.schemas import (
    ProgressTrackingCreate, 
    ProgressTrackingUpdate, 
    ProgressTrackingResponse
)
from app.api.dependencies import get_current_user
from app.models.models import User

router = APIRouter(prefix="/progress", tags=["进度跟踪"])

@router.post("/", response_model=ProgressTrackingResponse)
def create_progress_track(
    progress: ProgressTrackingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建进度跟踪记录"""
    # 检查待办事项是否存在且用户有权更新
    from app.crud.todo import get_todo
    todo = get_todo(db, progress.todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在"
        )
    
    # 检查用户权限（任务所有者、被分配者或共享清单成员）
    has_permission = False
    
    # 任务所有者
    if todo.user_id == current_user.id:
        has_permission = True
    else:
        # 检查是否被分配了此任务
        from app.crud.assignment import get_assignments_by_todo
        assignments = get_assignments_by_todo(db, progress.todo_id)
        if any(a.assignee_id == current_user.id and a.status == "accepted" for a in assignments):
            has_permission = True
        else:
            # 检查共享清单权限
            from app.crud.shared_list import get_shared_list_by_todo
            shared_list = get_shared_list_by_todo(db, progress.todo_id)
            if shared_list:
                member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
                if member:
                    has_permission = True
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限更新此任务进度"
        )
    
    return progress_crud.create_progress_track(db, progress, current_user.id)

@router.get("/{progress_id}", response_model=ProgressTrackingResponse)
def get_progress_track(
    progress_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取进度跟踪记录详情"""
    progress = progress_crud.get_progress_track(db, progress_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="进度跟踪记录不存在"
        )
    
    # 检查权限（记录创建者、任务所有者或共享清单成员）
    todo_owner_id = progress.todo.user_id
    has_permission = (
        current_user.id == progress.user_id or  # 记录创建者
        current_user.id == todo_owner_id or     # 任务所有者
        False
    )
    
    # 如果还不是权限拥有者，检查共享清单权限
    if not has_permission:
        from app.crud.shared_list import get_shared_list_by_todo
        shared_list = get_shared_list_by_todo(db, progress.todo_id)
        if shared_list:
            member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
            if member:
                has_permission = True
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此进度记录"
        )
    
    return progress

@router.get("/todo/{todo_id}", response_model=List[ProgressTrackingResponse])
def get_progress_tracks_by_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待办事项的所有进度跟踪记录"""
    # 检查待办事项权限
    from app.crud.todo import get_todo
    todo = get_todo(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在"
        )
    
    # 检查用户权限
    has_permission = False
    
    if todo.user_id == current_user.id:
        has_permission = True
    else:
        from app.crud.shared_list import get_shared_list_by_todo
        shared_list = get_shared_list_by_todo(db, todo_id)
        if shared_list:
            member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
            if member:
                has_permission = True
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此任务的进度记录"
        )
    
    return progress_crud.get_progress_tracks_by_todo(db, todo_id)

@router.put("/{progress_id}", response_model=ProgressTrackingResponse)
def update_progress_track(
    progress_id: int,
    progress_update: ProgressTrackingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新进度跟踪记录"""
    progress = progress_crud.get_progress_track(db, progress_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="进度跟踪记录不存在"
        )
    
    # 只有记录创建者可以更新
    if current_user.id != progress.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限修改此进度记录"
        )
    
    updated_progress = progress_crud.update_progress_track(db, progress_id, progress_update)
    if not updated_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="进度记录更新失败"
        )
    
    return updated_progress

@router.delete("/{progress_id}")
def delete_progress_track(
    progress_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除进度跟踪记录"""
    progress = progress_crud.get_progress_track(db, progress_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="进度跟踪记录不存在"
        )
    
    # 只有记录创建者可以删除
    if current_user.id != progress.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限删除此进度记录"
        )
    
    if not progress_crud.delete_progress_track(db, progress_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除进度记录失败"
        )
    
    return {"message": "进度记录删除成功"}

@router.get("/todo/{todo_id}/latest", response_model=ProgressTrackingResponse)
def get_latest_progress(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待办事项最新进度"""
    # 检查权限（同获取进度记录）
    from app.crud.todo import get_todo
    todo = get_todo(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在"
        )
    
    has_permission = False
    if todo.user_id == current_user.id:
        has_permission = True
    else:
        from app.crud.shared_list import get_shared_list_by_todo
        shared_list = get_shared_list_by_todo(db, todo_id)
        if shared_list:
            member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
            if member:
                has_permission = True
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此任务进度"
        )
    
    latest_progress = progress_crud.get_latest_progress(db, todo_id)
    if not latest_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无进度记录"
        )
    
    return latest_progress

@router.post("/todo/{todo_id}/status", response_model=ProgressTrackingResponse)
def update_progress_status(
    todo_id: int,
    status: str,
    progress_percentage: int = None,
    notes: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """快速更新任务进度状态"""
    # 检查权限（同创建进度记录）
    from app.crud.todo import get_todo
    todo = get_todo(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在"
        )
    
    has_permission = False
    if todo.user_id == current_user.id:
        has_permission = True
    else:
        from app.crud.assignment import get_assignments_by_todo
        assignments = get_assignments_by_todo(db, todo_id)
        if any(a.assignee_id == current_user.id and a.status == "accepted" for a in assignments):
            has_permission = True
        else:
            from app.crud.shared_list import get_shared_list_by_todo
            shared_list = get_shared_list_by_todo(db, todo_id)
            if shared_list:
                member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
                if member:
                    has_permission = True
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限更新此任务进度"
        )
    
    # 验证状态值
    try:
        from app.models.models import ProgressStatusEnum
        status_enum = ProgressStatusEnum(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的进度状态"
        )
    
    return progress_crud.update_progress_status(
        db, todo_id, current_user.id, status_enum, progress_percentage, notes
    )

@router.get("/user/{user_id}", response_model=List[ProgressTrackingResponse])
def get_progress_tracks_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的所有进度记录"""
    # 用户只能查看自己的进度记录
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看其他用户的进度记录"
        )
    
    return progress_crud.get_progress_tracks_by_user(db, user_id)

@router.get("/team/summary", response_model=dict)
def get_team_progress_summary(
    todo_ids: str,  # 逗号分隔的todo_id列表
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取团队任务进度汇总"""
    try:
        todo_id_list = [int(x.strip()) for x in todo_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务ID格式"
        )
    
    if not todo_id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供有效的任务ID"
        )
    
    # 验证用户对这些任务的访问权限
    from app.crud.todo import get_todo
    accessible_todos = []
    for todo_id in todo_id_list:
        todo = get_todo(db, todo_id)
        if todo:
            # 检查权限
            if (todo.user_id == current_user.id or 
                any(m.user_id == current_user.id for m in getattr(todo, 'shared_list_members', []))):
                accessible_todos.append(todo_id)
    
    if not accessible_todos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看这些任务的进度"
        )
    
    return progress_crud.get_team_progress_summary(db, accessible_todos)