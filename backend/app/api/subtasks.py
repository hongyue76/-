from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas import schemas
from app.models import models

router = APIRouter()

@router.post("/{parent_id}/children", response_model=schemas.TodoResponse)
def create_subtask(
    parent_id: int,
    subtask: schemas.SubtaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """为指定任务创建子任务"""
    # 验证父任务存在且属于当前用户
    parent_todo = db.query(models.Todo).filter(
        models.Todo.id == parent_id,
        models.Todo.user_id == current_user.id
    ).first()
    
    if not parent_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="父任务不存在或无权限访问"
        )
    
    # 创建子任务
    db_subtask = models.Todo(
        title=subtask.title,
        description=subtask.description,
        priority=subtask.priority,
        due_date=subtask.due_date,
        user_id=current_user.id,
        parent_id=parent_id
    )
    
    db.add(db_subtask)
    db.commit()
    db.refresh(db_subtask)
    
    return db_subtask

@router.get("/{todo_id}/children", response_model=List[schemas.TodoResponse])
def get_subtasks(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取指定任务的所有直接子任务"""
    # 验证任务存在且属于当前用户
    todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    # 获取直接子任务
    subtasks = db.query(models.Todo).filter(
        models.Todo.parent_id == todo_id,
        models.Todo.user_id == current_user.id
    ).all()
    
    return subtasks

@router.get("/{todo_id}/tree", response_model=schemas.TodoTreeResponse)
def get_task_tree(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取任务的完整子树结构"""
    # 验证任务存在且属于当前用户
    todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    def build_tree(todo_obj):
        # 获取直接子任务
        children = db.query(models.Todo).filter(
            models.Todo.parent_id == todo_obj.id,
            models.Todo.user_id == current_user.id
        ).all()
        
        # 递归构建子树
        tree_children = [build_tree(child) for child in children]
        
        # 返回树节点
        return schemas.TodoTreeResponse(
            id=todo_obj.id,
            title=todo_obj.title,
            description=todo_obj.description,
            priority=todo_obj.priority,
            category=todo_obj.category,
            due_date=todo_obj.due_date,
            completed=todo_obj.completed,
            completed_at=todo_obj.completed_at,
            created_at=todo_obj.created_at,
            updated_at=todo_obj.updated_at,
            user_id=todo_obj.user_id,
            parent_id=todo_obj.parent_id,
            has_children=len(children) > 0,
            children_count=len(children),
            children=tree_children
        )
    
    return build_tree(todo)

@router.put("/{todo_id}/move", response_model=schemas.TodoResponse)
def move_task(
    todo_id: int,
    move_data: schemas.SubtaskMove,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """移动任务到新的父级"""
    # 验证任务存在且属于当前用户
    todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    # 验证新父任务（如果指定了的话）
    if move_data.new_parent_id is not None:
        new_parent = db.query(models.Todo).filter(
            models.Todo.id == move_data.new_parent_id,
            models.Todo.user_id == current_user.id
        ).first()
        
        if not new_parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标父任务不存在或无权限访问"
            )
        
        # 检查循环引用（不能将任务移动到自己的子树下）
        def check_circular_reference(parent_id, target_id):
            if parent_id == target_id:
                return True
            parent = db.query(models.Todo).filter(models.Todo.id == parent_id).first()
            if parent and parent.parent_id:
                return check_circular_reference(parent.parent_id, target_id)
            return False
        
        if check_circular_reference(move_data.new_parent_id, todo_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将任务移动到自己的子树下"
            )
    
    # 执行移动操作
    todo.parent_id = move_data.new_parent_id
    db.commit()
    db.refresh(todo)
    
    return todo

@router.get("/roots", response_model=List[schemas.TodoResponse])
def get_root_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取所有根级别的任务（没有父任务的任务）"""
    root_tasks = db.query(models.Todo).filter(
        models.Todo.user_id == current_user.id,
        models.Todo.parent_id.is_(None)
    ).all()
    
    # 为每个根任务添加子任务信息
    result = []
    for task in root_tasks:
        children_count = db.query(models.Todo).filter(
            models.Todo.parent_id == task.id
        ).count()
        
        task_dict = task.__dict__.copy()
        task_dict['has_children'] = children_count > 0
        task_dict['children_count'] = children_count
        result.append(schemas.TodoResponse(**task_dict))
    
    return result

@router.delete("/{todo_id}/cascade", response_model=dict)
def delete_task_cascade(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """级联删除任务及其所有子任务"""
    # 验证任务存在且属于当前用户
    todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权限访问"
        )
    
    def get_all_descendants(parent_id):
        """递归获取所有后代任务ID"""
        children = db.query(models.Todo.id).filter(
            models.Todo.parent_id == parent_id
        ).all()
        
        descendant_ids = [child.id for child in children]
        for child_id in descendant_ids[:]:  # 使用切片复制避免迭代时修改
            descendant_ids.extend(get_all_descendants(child_id))
        
        return descendant_ids
    
    # 获取所有需要删除的任务ID
    all_ids_to_delete = [todo_id] + get_all_descendants(todo_id)
    
    # 执行删除
    db.query(models.Todo).filter(
        models.Todo.id.in_(all_ids_to_delete)
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "message": f"成功删除任务及其 {len(all_ids_to_delete) - 1} 个子任务",
        "deleted_count": len(all_ids_to_delete)
    }