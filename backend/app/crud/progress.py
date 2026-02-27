from sqlalchemy.orm import Session
from app.models.models import ProgressTracking, ProgressStatusEnum
from app.schemas.schemas import ProgressTrackingCreate, ProgressTrackingUpdate
from datetime import datetime
from typing import List, Optional

def get_progress_track(db: Session, progress_id: int) -> Optional[ProgressTracking]:
    """获取进度跟踪记录"""
    return db.query(ProgressTracking).filter(ProgressTracking.id == progress_id).first()

def get_progress_tracks_by_todo(db: Session, todo_id: int) -> List[ProgressTracking]:
    """获取待办事项的所有进度跟踪记录"""
    return db.query(ProgressTracking).filter(ProgressTracking.todo_id == todo_id).order_by(ProgressTracking.created_at.desc()).all()

def get_progress_tracks_by_user(db: Session, user_id: int) -> List[ProgressTracking]:
    """获取用户的所有进度跟踪记录"""
    return db.query(ProgressTracking).filter(ProgressTracking.user_id == user_id).order_by(ProgressTracking.created_at.desc()).all()

def create_progress_track(db: Session, progress: ProgressTrackingCreate, user_id: int) -> ProgressTracking:
    """创建进度跟踪记录"""
    db_progress = ProgressTracking(
        todo_id=progress.todo_id,
        user_id=user_id,
        status=progress.status,
        progress_percentage=progress.progress_percentage,
        notes=progress.notes,
        hours_spent=progress.hours_spent
    )
    db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress

def update_progress_track(db: Session, progress_id: int, progress_update: ProgressTrackingUpdate) -> Optional[ProgressTracking]:
    """更新进度跟踪记录"""
    db_progress = get_progress_track(db, progress_id)
    if not db_progress:
        return None
    
    update_data = progress_update.dict(exclude_unset=True)
    
    # 如果状态改变且变为完成，则更新完成时间
    if "status" in update_data and update_data["status"] == ProgressStatusEnum.DONE:
        update_data["completed_at"] = datetime.utcnow()
    
    for key, value in update_data.items():
        setattr(db_progress, key, value)
    
    db.commit()
    db.refresh(db_progress)
    return db_progress

def delete_progress_track(db: Session, progress_id: int) -> bool:
    """删除进度跟踪记录"""
    db_progress = get_progress_track(db, progress_id)
    if not db_progress:
        return False
    
    db.delete(db_progress)
    db.commit()
    return True

def get_latest_progress(db: Session, todo_id: int) -> Optional[ProgressTracking]:
    """获取待办事项最新的进度跟踪记录"""
    return db.query(ProgressTracking).filter(ProgressTracking.todo_id == todo_id).order_by(ProgressTracking.created_at.desc()).first()

def update_progress_status(db: Session, todo_id: int, user_id: int, status: ProgressStatusEnum, 
                          progress_percentage: int = None, notes: str = None) -> ProgressTracking:
    """更新任务进度状态"""
    # 先查找现有的进度记录
    existing_progress = db.query(ProgressTracking).filter(
        ProgressTracking.todo_id == todo_id,
        ProgressTracking.user_id == user_id
    ).order_by(ProgressTracking.created_at.desc()).first()
    
    if existing_progress:
        # 更新现有记录
        update_data = {"status": status}
        if progress_percentage is not None:
            update_data["progress_percentage"] = progress_percentage
        if notes is not None:
            update_data["notes"] = notes
            
        for key, value in update_data.items():
            setattr(existing_progress, key, value)
        existing_progress.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_progress)
        return existing_progress
    else:
        # 创建新记录
        return create_progress_track(db, ProgressTrackingCreate(
            todo_id=todo_id,
            status=status,
            progress_percentage=progress_percentage or 0,
            notes=notes
        ), user_id)

def get_team_progress_summary(db: Session, todo_ids: List[int]) -> dict:
    """获取团队任务进度汇总"""
    if not todo_ids:
        return {"total": 0, "todo": 0, "in_progress": 0, "review": 0, "done": 0, "completion_rate": 0}
    
    progresses = db.query(ProgressTracking).filter(
        ProgressTracking.todo_id.in_(todo_ids)
    ).order_by(ProgressTracking.todo_id, ProgressTracking.created_at.desc()).all()
    
    # 获取每个任务的最新进度
    latest_progress = {}
    for progress in progresses:
        if progress.todo_id not in latest_progress:
            latest_progress[progress.todo_id] = progress
    
    total = len(todo_ids)
    status_counts = {
        "todo": 0,
        "in_progress": 0,
        "review": 0,
        "done": 0
    }
    
    for progress in latest_progress.values():
        status_counts[progress.status.value] += 1
    
    completion_rate = (status_counts["done"] / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "todo": status_counts["todo"],
        "in_progress": status_counts["in_progress"],
        "review": status_counts["review"],
        "done": status_counts["done"],
        "completion_rate": round(completion_rate, 2)
    }