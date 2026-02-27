from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas
from typing import List
from datetime import datetime

def get_shared_list(db: Session, list_id: int):
    return db.query(models.SharedList).filter(models.SharedList.id == list_id).first()

def get_shared_lists_by_owner(db: Session, owner_id: int):
    return db.query(models.SharedList).filter(models.SharedList.owner_id == owner_id).all()

def get_shared_lists_by_member(db: Session, user_id: int):
    return db.query(models.SharedList).join(models.SharedListMember).filter(
        models.SharedListMember.user_id == user_id
    ).all()

def create_shared_list(db: Session, list_data: schemas.SharedListCreate, owner_id: int):
    db_list = models.SharedList(**list_data.dict(), owner_id=owner_id)
    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    
    # 自动将创建者添加为管理员成员
    member = models.SharedListMember(
        shared_list_id=db_list.id,
        user_id=owner_id,
        role="owner"
    )
    db.add(member)
    db.commit()
    
    return db_list

def update_shared_list(db: Session, list_id: int, list_update: schemas.SharedListCreate):
    db_list = get_shared_list(db, list_id)
    if db_list:
        for field, value in list_update.dict().items():
            setattr(db_list, field, value)
        db_list.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_list)
    return db_list

def delete_shared_list(db: Session, list_id: int):
    db_list = get_shared_list(db, list_id)
    if db_list:
        db.delete(db_list)
        db.commit()
    return db_list

# 成员管理功能
def add_member_to_list(db: Session, list_id: int, user_id: int, role: str = "member"):
    # 检查用户是否存在
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    # 检查是否已经是成员
    existing_member = db.query(models.SharedListMember).filter(
        models.SharedListMember.shared_list_id == list_id,
        models.SharedListMember.user_id == user_id
    ).first()
    
    if existing_member:
        return existing_member
    
    # 添加新成员
    member = models.SharedListMember(
        shared_list_id=list_id,
        user_id=user_id,
        role=role
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def remove_member_from_list(db: Session, list_id: int, user_id: int):
    member = db.query(models.SharedListMember).filter(
        models.SharedListMember.shared_list_id == list_id,
        models.SharedListMember.user_id == user_id
    ).first()
    
    if member:
        db.delete(member)
        db.commit()
        return True
    return False

def get_list_members(db: Session, list_id: int):
    return db.query(models.SharedListMember).filter(
        models.SharedListMember.shared_list_id == list_id
    ).all()

def update_member_role(db: Session, list_id: int, user_id: int, new_role: str):
    member = db.query(models.SharedListMember).filter(
        models.SharedListMember.shared_list_id == list_id,
        models.SharedListMember.user_id == user_id
    ).first()
    
    if member:
        member.role = new_role
        db.commit()
        db.refresh(member)
        return member
    return None

# 权限检查功能
def check_list_permission(db: Session, list_id: int, user_id: int, required_role: str = "member"):
    member = db.query(models.SharedListMember).filter(
        models.SharedListMember.shared_list_id == list_id,
        models.SharedListMember.user_id == user_id
    ).first()
    
    if not member:
        return False
    
    # 角色权限等级: owner > admin > member
    role_hierarchy = {"owner": 3, "admin": 2, "member": 1}
    
    user_role_level = role_hierarchy.get(member.role, 0)
    required_role_level = role_hierarchy.get(required_role, 0)
    
    return user_role_level >= required_role_level