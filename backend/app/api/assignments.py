from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.crud import assignment as assignment_crud
from app.schemas.schemas import (
    TaskAssignmentCreate, 
    TaskAssignmentUpdate, 
    TaskAssignmentResponse
)
from app.api.dependencies import get_current_user
from app.models.models import User

router = APIRouter(prefix="/assignments", tags=["任务分配"])

@router.post("/", response_model=TaskAssignmentResponse)
def create_assignment(
    assignment: TaskAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建任务分配"""
    # 检查待办事项是否存在且用户有权分配
    from app.crud.todo import get_todo
    todo = get_todo(db, assignment.todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在"
        )
    
    # 检查用户是否有权限分配此任务（任务所有者或共享清单管理员）
    if todo.user_id != current_user.id:
        # 检查是否在共享清单中且有分配权限
        from app.crud.shared_list import get_shared_list_by_todo
        shared_list = get_shared_list_by_todo(db, assignment.todo_id)
        if not shared_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限分配此任务"
            )
        
        # 检查用户是否是共享清单的管理员
        member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
        if not member or member.role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限分配此任务"
            )
    
    # 检查被分配者是否存在
    from app.crud.user import get_user
    assignee = get_user(db, assignment.assignee_id)
    if not assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="被分配用户不存在"
        )
    
    # 检查是否已经分配给该用户
    existing_assignments = assignment_crud.get_assignments_by_todo(db, assignment.todo_id)
    if any(a.assignee_id == assignment.assignee_id for a in existing_assignments):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该任务已分配给此用户"
        )
    
    return assignment_crud.create_assignment(db, assignment, current_user.id)

@router.get("/{assignment_id}", response_model=TaskAssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务分配详情"""
    assignment = assignment_crud.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配不存在"
        )
    
    # 检查权限（分配者、被分配者或任务所有者）
    todo_owner_id = assignment.todo.user_id
    if not (current_user.id in [assignment.assigner_id, assignment.assignee_id, todo_owner_id]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此任务分配"
        )
    
    return assignment

@router.get("/todo/{todo_id}", response_model=List[TaskAssignmentResponse])
def get_assignments_by_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待办事项的所有任务分配"""
    # 检查待办事项权限
    from app.crud.todo import get_todo
    todo = get_todo(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在"
        )
    
    # 检查用户是否有权限查看（任务所有者或共享清单成员）
    if todo.user_id != current_user.id:
        from app.crud.shared_list import get_shared_list_by_todo
        shared_list = get_shared_list_by_todo(db, todo_id)
        if not shared_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限查看此任务的分配信息"
            )
        
        member = next((m for m in shared_list.members if m.user_id == current_user.id), None)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限查看此任务的分配信息"
            )
    
    return assignment_crud.get_assignments_by_todo(db, todo_id)

@router.put("/{assignment_id}", response_model=TaskAssignmentResponse)
def update_assignment(
    assignment_id: int,
    assignment_update: TaskAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新任务分配"""
    assignment = assignment_crud.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配不存在"
        )
    
    # 检查权限（只有分配者可以修改状态）
    if current_user.id != assignment.assigner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限修改此任务分配"
        )
    
    updated_assignment = assignment_crud.update_assignment(db, assignment_id, assignment_update)
    if not updated_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配更新失败"
        )
    
    return updated_assignment

@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除任务分配"""
    assignment = assignment_crud.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配不存在"
        )
    
    # 检查权限（分配者或被分配者可以删除）
    if current_user.id not in [assignment.assigner_id, assignment.assignee_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限删除此任务分配"
        )
    
    if not assignment_crud.delete_assignment(db, assignment_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除任务分配失败"
        )
    
    return {"message": "任务分配删除成功"}

@router.post("/{assignment_id}/accept", response_model=TaskAssignmentResponse)
def accept_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """接受任务分配"""
    assignment = assignment_crud.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配不存在"
        )
    
    # 只有被分配者可以接受
    if current_user.id != assignment.assignee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限接受此任务分配"
        )
    
    if assignment.status != "assigned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务分配状态不允许接受"
        )
    
    accepted_assignment = assignment_crud.accept_assignment(db, assignment_id)
    if not accepted_assignment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="接受任务分配失败"
        )
    
    return accepted_assignment

@router.post("/{assignment_id}/reject", response_model=TaskAssignmentResponse)
def reject_assignment(
    assignment_id: int,
    rejection_reason: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """拒绝任务分配"""
    assignment = assignment_crud.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配不存在"
        )
    
    # 只有被分配者可以拒绝
    if current_user.id != assignment.assignee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限拒绝此任务分配"
        )
    
    if assignment.status != "assigned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务分配状态不允许拒绝"
        )
    
    rejected_assignment = assignment_crud.reject_assignment(db, assignment_id, rejection_reason)
    if not rejected_assignment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="拒绝任务分配失败"
        )
    
    return rejected_assignment

@router.get("/user/pending", response_model=List[TaskAssignmentResponse])
def get_pending_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户待处理的任务分配"""
    return assignment_crud.get_pending_assignments(db, current_user.id)

@router.post("/{assignment_id}/complete", response_model=TaskAssignmentResponse)
def complete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记任务分配为完成"""
    assignment = assignment_crud.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务分配不存在"
        )
    
    # 只有被分配者可以标记完成
    if current_user.id != assignment.assignee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限完成此任务分配"
        )
    
    if assignment.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能完成已接受的任务分配"
        )
    
    completed_assignment = assignment_crud.complete_assignment(db, assignment_id)
    if not completed_assignment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="完成任务分配失败"
        )
    
    return completed_assignment