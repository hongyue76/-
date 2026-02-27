from sqlalchemy.orm import Session
from app.models.models import TaskAssignment, AssignmentStatusEnum
from app.schemas.schemas import TaskAssignmentCreate, TaskAssignmentUpdate
from datetime import datetime
from typing import List, Optional

def get_assignment(db: Session, assignment_id: int) -> Optional[TaskAssignment]:
    """获取任务分配"""
    return db.query(TaskAssignment).filter(TaskAssignment.id == assignment_id).first()

def get_assignments_by_todo(db: Session, todo_id: int) -> List[TaskAssignment]:
    """获取待办事项的所有任务分配"""
    return db.query(TaskAssignment).filter(TaskAssignment.todo_id == todo_id).all()

def get_assignments_by_assignee(db: Session, assignee_id: int) -> List[TaskAssignment]:
    """获取用户被分配的所有任务"""
    return db.query(TaskAssignment).filter(TaskAssignment.assignee_id == assignee_id).all()

def get_assignments_by_assigner(db: Session, assigner_id: int) -> List[TaskAssignment]:
    """获取用户分配的所有任务"""
    return db.query(TaskAssignment).filter(TaskAssignment.assigner_id == assigner_id).all()

def create_assignment(db: Session, assignment: TaskAssignmentCreate, assigner_id: int) -> TaskAssignment:
    """创建任务分配"""
    db_assignment = TaskAssignment(
        todo_id=assignment.todo_id,
        assigner_id=assigner_id,
        assignee_id=assignment.assignee_id,
        status=AssignmentStatusEnum.ASSIGNED
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def update_assignment(db: Session, assignment_id: int, assignment_update: TaskAssignmentUpdate) -> Optional[TaskAssignment]:
    """更新任务分配"""
    db_assignment = get_assignment(db, assignment_id)
    if not db_assignment:
        return None
    
    update_data = assignment_update.dict(exclude_unset=True)
    
    # 处理特殊状态更新
    if "status" in update_data:
        status = update_data["status"]
        if status == AssignmentStatusEnum.ACCEPTED:
            update_data["accepted_at"] = datetime.utcnow()
        elif status == AssignmentStatusEnum.REJECTED:
            update_data["rejected_at"] = datetime.utcnow()
        elif status == AssignmentStatusEnum.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
    
    for key, value in update_data.items():
        setattr(db_assignment, key, value)
    
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def delete_assignment(db: Session, assignment_id: int) -> bool:
    """删除任务分配"""
    db_assignment = get_assignment(db, assignment_id)
    if not db_assignment:
        return False
    
    db.delete(db_assignment)
    db.commit()
    return True

def get_pending_assignments(db: Session, user_id: int) -> List[TaskAssignment]:
    """获取用户待处理的任务分配（已分配但未接受/拒绝）"""
    return db.query(TaskAssignment).filter(
        TaskAssignment.assignee_id == user_id,
        TaskAssignment.status == AssignmentStatusEnum.ASSIGNED
    ).all()

def accept_assignment(db: Session, assignment_id: int) -> Optional[TaskAssignment]:
    """接受任务分配"""
    return update_assignment(db, assignment_id, TaskAssignmentUpdate(status=AssignmentStatusEnum.ACCEPTED))

def reject_assignment(db: Session, assignment_id: int, rejection_reason: str = None) -> Optional[TaskAssignment]:
    """拒绝任务分配"""
    return update_assignment(db, assignment_id, TaskAssignmentUpdate(
        status=AssignmentStatusEnum.REJECTED,
        rejection_reason=rejection_reason
    ))

def complete_assignment(db: Session, assignment_id: int) -> Optional[TaskAssignment]:
    """完成任务分配"""
    return update_assignment(db, assignment_id, TaskAssignmentUpdate(status=AssignmentStatusEnum.COMPLETED))