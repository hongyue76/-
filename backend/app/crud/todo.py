from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas
from typing import List, Optional
from datetime import datetime

def get_todo(db: Session, todo_id: int, user_id: int):
    return db.query(models.Todo).filter(
        models.Todo.id == todo_id,
        models.Todo.user_id == user_id
    ).first()

def get_todos(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Todo).filter(
        models.Todo.user_id == user_id
    ).offset(skip).limit(limit).all()

def get_todos_by_category(db: Session, user_id: int, category: str):
    return db.query(models.Todo).filter(
        models.Todo.user_id == user_id,
        models.Todo.category == category
    ).all()

def create_todo(db: Session, todo: schemas.TodoCreate, user_id: int):
    db_todo = models.Todo(**todo.dict(), user_id=user_id)
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, user_id: int, todo_update: schemas.TodoUpdate):
    db_todo = get_todo(db, todo_id, user_id)
    if db_todo:
        update_data = todo_update.dict(exclude_unset=True)
        if 'completed' in update_data and update_data['completed']:
            update_data['completed_at'] = datetime.utcnow()
        elif 'completed' in update_data and not update_data['completed']:
            update_data['completed_at'] = None
            
        for field, value in update_data.items():
            setattr(db_todo, field, value)
        db.commit()
        db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int, user_id: int):
    db_todo = get_todo(db, todo_id, user_id)
    if db_todo:
        db.delete(db_todo)
        db.commit()
    return db_todo

def get_completed_todos_count(db: Session, user_id: int):
    return db.query(models.Todo).filter(
        models.Todo.user_id == user_id,
        models.Todo.completed == True
    ).count()

def get_pending_todos_count(db: Session, user_id: int):
    return db.query(models.Todo).filter(
        models.Todo.user_id == user_id,
        models.Todo.completed == False
    ).count()