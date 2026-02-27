from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.schemas import schemas
from app.models import models

router = APIRouter()

@router.get("/me", response_model=schemas.UserResponse)
def read_user(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
def update_user(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.crud import user as user_crud
    updated_user = user_crud.update_user(db, current_user.id, user_update)
    return updated_user