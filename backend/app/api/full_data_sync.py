"""
全量数据同步API
提供完整的数据导出和增量同步功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models import models
from app.schemas import schemas
from app.api.auth import get_current_user
import json

router = APIRouter(prefix="/full-sync", tags=["全量同步"])

@router.get("/export")
async def export_all_user_data(
    since: Optional[datetime] = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """导出用户所有数据"""
    
    try:
        # 获取用户的所有任务
        todos_query = db.query(models.Todo).filter(
            models.Todo.user_id == current_user.id
        )
        
        if not include_deleted:
            todos_query = todos_query.filter(models.Todo.deleted == False)
        
        if since:
            todos_query = todos_query.filter(models.Todo.updated_at > since)
        
        todos = todos_query.all()
        
        # 获取用户的评论
        comments_query = db.query(models.Comment).filter(
            models.Comment.user_id == current_user.id
        )
        
        if since:
            comments_query = comments_query.filter(models.Comment.created_at > since)
        
        comments = comments_query.all()
        
        # 获取任务分配
        assignments_query = db.query(models.TaskAssignment).filter(
            models.TaskAssignment.assignee_id == current_user.id
        )
        
        if since:
            assignments_query = assignments_query.filter(models.TaskAssignment.updated_at > since)
        
        assignments = assignments_query.all()
        
        # 获取共享清单
        shared_lists_query = db.query(models.SharedList).filter(
            models.SharedList.owner_id == current_user.id
        )
        
        if since:
            shared_lists_query = shared_lists_query.filter(models.SharedList.updated_at > since)
        
        owned_lists = shared_lists_query.all()
        
        # 获取作为成员的共享清单
        member_lists = db.query(models.SharedListMember).filter(
            models.SharedListMember.user_id == current_user.id
        ).all()
        
        member_list_ids = [member.list_id for member in member_lists]
        shared_member_lists = db.query(models.SharedList).filter(
            models.SharedList.id.in_(member_list_ids)
        ).all() if member_list_ids else []
        
        # 构建响应数据
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
            "user_username": current_user.username,
            "data": {
                "todos": [
                    {
                        "id": todo.id,
                        "title": todo.title,
                        "description": todo.description,
                        "completed": todo.completed,
                        "priority": todo.priority,
                        "category": todo.category,
                        "due_date": todo.due_date.isoformat() if todo.due_date else None,
                        "parent_id": todo.parent_id,
                        "created_at": todo.created_at.isoformat(),
                        "updated_at": todo.updated_at.isoformat(),
                        "version": todo.version
                    }
                    for todo in todos
                ],
                "comments": [
                    {
                        "id": comment.id,
                        "todo_id": comment.todo_id,
                        "content": comment.content,
                        "created_at": comment.created_at.isoformat(),
                        "updated_at": comment.updated_at.isoformat()
                    }
                    for comment in comments
                ],
                "assignments": [
                    {
                        "id": assignment.id,
                        "todo_id": assignment.todo_id,
                        "assigner_id": assignment.assigner_id,
                        "assignee_id": assignment.assignee_id,
                        "status": assignment.status,
                        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                        "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None
                    }
                    for assignment in assignments
                ],
                "owned_shared_lists": [
                    {
                        "id": shared_list.id,
                        "name": shared_list.name,
                        "description": shared_list.description,
                        "created_at": shared_list.created_at.isoformat(),
                        "updated_at": shared_list.updated_at.isoformat(),
                        "default_permission": shared_list.default_permission
                    }
                    for shared_list in owned_lists
                ],
                "member_shared_lists": [
                    {
                        "id": shared_list.id,
                        "name": shared_list.name,
                        "description": shared_list.description,
                        "owner_id": shared_list.owner_id,
                        "owner_username": shared_list.owner.username if shared_list.owner else "Unknown",
                        "permission": next(
                            (member.permission for member in member_lists if member.list_id == shared_list.id),
                            "viewer"
                        ),
                        "joined_at": next(
                            (member.joined_at.isoformat() for member in member_lists if member.list_id == shared_list.id),
                            None
                        )
                    }
                    for shared_list in shared_member_lists
                ]
            }
        }
        
        return export_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"数据导出失败: {str(e)}"
        )

@router.get("/incremental")
async def get_incremental_updates(
    since: datetime,
    entity_types: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取增量更新数据"""
    
    if not entity_types:
        entity_types = ["todos", "comments", "assignments"]
    
    updates = {}
    
    try:
        # 任务更新
        if "todos" in entity_types:
            todos_query = db.query(models.Todo).filter(
                models.Todo.user_id == current_user.id,
                models.Todo.updated_at > since
            ).order_by(models.Todo.updated_at.desc())
            
            total_todos = todos_query.count()
            todos = todos_query.offset((page - 1) * size).limit(size).all()
            
            updates["todos"] = {
                "items": [
                    {
                        "id": todo.id,
                        "title": todo.title,
                        "description": todo.description,
                        "completed": todo.completed,
                        "priority": todo.priority,
                        "updated_at": todo.updated_at.isoformat(),
                        "version": todo.version
                    }
                    for todo in todos
                ],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_todos,
                    "has_more": page * size < total_todos
                }
            }
        
        # 评论更新
        if "comments" in entity_types:
            comments_query = db.query(models.Comment).filter(
                models.Comment.user_id == current_user.id,
                models.Comment.updated_at > since
            ).order_by(models.Comment.updated_at.desc())
            
            total_comments = comments_query.count()
            comments = comments_query.offset((page - 1) * size).limit(size).all()
            
            updates["comments"] = {
                "items": [
                    {
                        "id": comment.id,
                        "todo_id": comment.todo_id,
                        "content": comment.content,
                        "updated_at": comment.updated_at.isoformat()
                    }
                    for comment in comments
                ],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_comments,
                    "has_more": page * size < total_comments
                }
            }
        
        # 任务分配更新
        if "assignments" in entity_types:
            assignments_query = db.query(models.TaskAssignment).filter(
                models.TaskAssignment.assignee_id == current_user.id,
                models.TaskAssignment.updated_at > since
            ).order_by(models.TaskAssignment.updated_at.desc())
            
            total_assignments = assignments_query.count()
            assignments = assignments_query.offset((page - 1) * size).limit(size).all()
            
            updates["assignments"] = {
                "items": [
                    {
                        "id": assignment.id,
                        "todo_id": assignment.todo_id,
                        "status": assignment.status,
                        "updated_at": assignment.updated_at.isoformat(),
                        "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None
                    }
                    for assignment in assignments
                ],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_assignments,
                    "has_more": page * size < total_assignments
                }
            }
        
        return {
            "since": since.isoformat(),
            "current_time": datetime.utcnow().isoformat(),
            "updates": updates
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取增量更新失败: {str(e)}"
        )

@router.post("/import")
async def import_user_data(
    import_data: Dict[str, Any],
    clear_existing: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """导入用户数据"""
    
    try:
        imported_counts = {
            "todos": 0,
            "comments": 0,
            "assignments": 0
        }
        
        # 如果需要清空现有数据
        if clear_existing:
            # 删除用户现有的任务、评论等
            db.query(models.Comment).filter(
                models.Comment.user_id == current_user.id
            ).delete()
            
            db.query(models.TaskAssignment).filter(
                models.TaskAssignment.assignee_id == current_user.id
            ).delete()
            
            db.query(models.Todo).filter(
                models.Todo.user_id == current_user.id
            ).delete()
            
            db.commit()
        
        # 导入任务
        if "todos" in import_data:
            for todo_data in import_data["todos"]:
                todo = models.Todo(
                    user_id=current_user.id,
                    title=todo_data["title"],
                    description=todo_data.get("description"),
                    completed=todo_data.get("completed", False),
                    priority=todo_data.get("priority", "medium"),
                    category=todo_data.get("category", "默认"),
                    due_date=datetime.fromisoformat(todo_data["due_date"]) if todo_data.get("due_date") else None,
                    parent_id=todo_data.get("parent_id"),
                    version=todo_data.get("version", 1)
                )
                db.add(todo)
                imported_counts["todos"] += 1
            
            db.commit()
        
        # 导入评论（需要先导入任务）
        if "comments" in import_data:
            for comment_data in import_data["comments"]:
                comment = models.Comment(
                    todo_id=comment_data["todo_id"],
                    user_id=current_user.id,
                    content=comment_data["content"]
                )
                db.add(comment)
                imported_counts["comments"] += 1
            
            db.commit()
        
        # 导入任务分配
        if "assignments" in import_data:
            for assignment_data in import_data["assignments"]:
                assignment = models.TaskAssignment(
                    todo_id=assignment_data["todo_id"],
                    assigner_id=assignment_data["assigner_id"],
                    assignee_id=current_user.id,
                    status=assignment_data.get("status", "pending")
                )
                db.add(assignment)
                imported_counts["assignments"] += 1
            
            db.commit()
        
        return {
            "message": "数据导入成功",
            "imported_counts": imported_counts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"数据导入失败: {str(e)}"
        )

@router.get("/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取用户数据同步状态"""
    
    try:
        # 获取各种数据的最新更新时间
        latest_todo = db.query(models.Todo).filter(
            models.Todo.user_id == current_user.id
        ).order_by(models.Todo.updated_at.desc()).first()
        
        latest_comment = db.query(models.Comment).filter(
            models.Comment.user_id == current_user.id
        ).order_by(models.Comment.updated_at.desc()).first()
        
        latest_assignment = db.query(models.TaskAssignment).filter(
            models.TaskAssignment.assignee_id == current_user.id
        ).order_by(models.TaskAssignment.updated_at.desc()).first()
        
        return {
            "user_id": current_user.id,
            "last_todo_update": latest_todo.updated_at.isoformat() if latest_todo else None,
            "last_comment_update": latest_comment.updated_at.isoformat() if latest_comment else None,
            "last_assignment_update": latest_assignment.updated_at.isoformat() if latest_assignment else None,
            "server_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取同步状态失败: {str(e)}"
        )

# Schema定义
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ImportDataRequest(BaseModel):
    todos: Optional[List[Dict[str, Any]]] = None
    comments: Optional[List[Dict[str, Any]]] = None
    assignments: Optional[List[Dict[str, Any]]] = None
    shared_lists: Optional[List[Dict[str, Any]]] = None

class ExportDataResponse(BaseModel):
    export_timestamp: str
    user_id: int
    user_username: str
    data: Dict[str, Any]