from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas
from typing import List
from datetime import datetime

def get_comment(db: Session, comment_id: int):
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()

def get_comments_by_todo(db: Session, todo_id: int):
    return db.query(models.Comment).filter(models.Comment.todo_id == todo_id).order_by(
        models.Comment.created_at.desc()
    ).all()

def create_comment(db: Session, comment_data: schemas.CommentCreate, todo_id: int, user_id: int):
    db_comment = models.Comment(
        **comment_data.dict(),
        todo_id=todo_id,
        user_id=user_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

def update_comment(db: Session, comment_id: int, comment_update: schemas.CommentCreate, user_id: int):
    db_comment = get_comment(db, comment_id)
    if db_comment and db_comment.user_id == user_id:
        db_comment.content = comment_update.content
        db_comment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_comment)
        return db_comment
    return None

def delete_comment(db: Session, comment_id: int, user_id: int):
    db_comment = get_comment(db, comment_id)
    if db_comment and db_comment.user_id == user_id:
        db.delete(db_comment)
        db.commit()
        return True
    return False

def get_user_comments(db: Session, user_id: int, limit: int = 50):
    return db.query(models.Comment).filter(models.Comment.user_id == user_id).order_by(
        models.Comment.created_at.desc()
    ).limit(limit).all()