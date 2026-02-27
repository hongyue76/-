from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.crud import comment as comment_crud
from app.schemas import schemas
from app.models import models

router = APIRouter(prefix="/comments", tags=["评论"])

@router.post("/todos/{todo_id}", response_model=schemas.CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    todo_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """为待办事项添加评论"""
    # 验证待办事项存在且用户有权访问
    from app.crud import todo as todo_crud
    todo = todo_crud.get_todo(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    
    return comment_crud.create_comment(db=db, comment_data=comment, todo_id=todo_id, user_id=current_user.id)

@router.get("/todos/{todo_id}", response_model=List[schemas.CommentResponse])
def get_todo_comments(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取待办事项的所有评论"""
    # 验证待办事项存在且用户有权访问
    from app.crud import todo as todo_crud
    todo = todo_crud.get_todo(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    
    comments = comment_crud.get_comments_by_todo(db, todo_id)
    return comments

@router.put("/{comment_id}", response_model=schemas.CommentResponse)
def update_comment(
    comment_id: int,
    comment_update: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """更新评论（仅评论作者）"""
    db_comment = comment_crud.get_comment(db, comment_id)
    if not db_comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    if db_comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能修改自己的评论")
    
    updated_comment = comment_crud.update_comment(db, comment_id, comment_update, current_user.id)
    if not updated_comment:
        raise HTTPException(status_code=400, detail="更新失败")
    
    return updated_comment

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """删除评论（仅评论作者）"""
    db_comment = comment_crud.get_comment(db, comment_id)
    if not db_comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    if db_comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的评论")
    
    success = comment_crud.delete_comment(db, comment_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="删除失败")
    
    return

@router.get("/user/{user_id}", response_model=List[schemas.CommentResponse])
def get_user_comments(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取用户的所有评论"""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能查看自己的评论")
    
    comments = comment_crud.get_user_comments(db, user_id, limit)
    return comments