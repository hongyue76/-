from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.crud import todo as todo_crud
from app.schemas import schemas
from app.models import models

router = APIRouter()

@router.post("/", response_model=schemas.TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo: schemas.TodoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return todo_crud.create_todo(db=db, todo=todo, user_id=current_user.id)

@router.get("/", response_model=List[schemas.TodoResponse])
def read_todos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    todos = todo_crud.get_todos(db, user_id=current_user.id, skip=skip, limit=limit)
    return todos

@router.get("/{todo_id}", response_model=schemas.TodoResponse)
def read_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_todo = todo_crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    return db_todo

@router.put("/{todo_id}", response_model=schemas.TodoResponse)
def update_todo(
    todo_id: int,
    todo: schemas.TodoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_todo = todo_crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    return todo_crud.update_todo(db=db, todo_id=todo_id, user_id=current_user.id, todo_update=todo)

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_todo = todo_crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    todo_crud.delete_todo(db=db, todo_id=todo_id, user_id=current_user.id)
    return

@router.get("/category/{category}", response_model=List[schemas.TodoResponse])
def get_todos_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    todos = todo_crud.get_todos_by_category(db, user_id=current_user.id, category=category)
    return todos

@router.get("/stats/completion")
def get_completion_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    completed = todo_crud.get_completed_todos_count(db, user_id=current_user.id)
    pending = todo_crud.get_pending_todos_count(db, user_id=current_user.id)
    total = completed + pending
    
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": round(completed / total * 100, 2) if total > 0 else 0
    }