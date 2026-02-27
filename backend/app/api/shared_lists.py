from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.crud import shared_list as shared_list_crud
from app.schemas import schemas
from app.models import models

router = APIRouter(prefix="/shared-lists", tags=["共享清单"])

@router.post("/", response_model=schemas.SharedListResponse, status_code=status.HTTP_201_CREATED)
def create_shared_list(
    list_data: schemas.SharedListCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """创建新的共享清单"""
    return shared_list_crud.create_shared_list(db=db, list_data=list_data, owner_id=current_user.id)

@router.get("/", response_model=List[schemas.SharedListResponse])
def get_my_shared_lists(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取我创建的所有共享清单"""
    lists = shared_list_crud.get_shared_lists_by_owner(db, owner_id=current_user.id)
    return lists

@router.get("/member", response_model=List[schemas.SharedListResponse])
def get_shared_lists_i_joined(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取我参与的所有共享清单"""
    lists = shared_list_crud.get_shared_lists_by_member(db, user_id=current_user.id)
    return lists

@router.get("/{list_id}", response_model=schemas.SharedListResponse)
def get_shared_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取特定共享清单详情"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 检查用户是否有访问权限
    if not shared_list_crud.check_list_permission(db, list_id, current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此清单")
    
    return db_list

@router.put("/{list_id}", response_model=schemas.SharedListResponse)
def update_shared_list(
    list_id: int,
    list_data: schemas.SharedListCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """更新共享清单信息"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 只有所有者或管理员可以修改清单信息
    if not shared_list_crud.check_list_permission(db, list_id, current_user.id, "admin"):
        raise HTTPException(status_code=403, detail="无权修改此清单")
    
    return shared_list_crud.update_shared_list(db=db, list_id=list_id, list_update=list_data)

@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shared_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """删除共享清单（仅所有者）"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 只有所有者可以删除清单
    if db_list.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有清单创建者可以删除")
    
    shared_list_crud.delete_shared_list(db=db, list_id=list_id)
    return

# 成员管理API
@router.post("/{list_id}/members/{user_id}")
def add_member(
    list_id: int,
    user_id: int,
    role: str = "member",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """添加成员到共享清单"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 只有所有者或管理员可以添加成员
    if not shared_list_crud.check_list_permission(db, list_id, current_user.id, "admin"):
        raise HTTPException(status_code=403, detail="无权添加成员")
    
    member = shared_list_crud.add_member_to_list(db, list_id, user_id, role)
    if not member:
        raise HTTPException(status_code=400, detail="用户不存在或已是成员")
    
    return {"message": "成员添加成功", "member": member}

@router.delete("/{list_id}/members/{user_id}")
def remove_member(
    list_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """从共享清单移除成员"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 不能移除自己（除非是所有者）
    if user_id == current_user.id and db_list.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="不能移除自己")
    
    # 只有所有者或管理员可以移除成员
    if not shared_list_crud.check_list_permission(db, list_id, current_user.id, "admin"):
        raise HTTPException(status_code=403, detail="无权移除成员")
    
    # 所有者不能被移除
    if user_id == db_list.owner_id:
        raise HTTPException(status_code=400, detail="不能移除清单创建者")
    
    success = shared_list_crud.remove_member_from_list(db, list_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    return {"message": "成员移除成功"}

@router.put("/{list_id}/members/{user_id}/role")
def update_member_role(
    list_id: int,
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """更新成员角色"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 只有所有者可以修改角色
    if db_list.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有清单创建者可以修改角色")
    
    # 不能修改自己的角色
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    
    member = shared_list_crud.update_member_role(db, list_id, user_id, role)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    return {"message": "角色更新成功", "member": member}

@router.get("/{list_id}/members")
def get_list_members(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取清单所有成员"""
    db_list = shared_list_crud.get_shared_list(db, list_id=list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="共享清单不存在")
    
    # 检查访问权限
    if not shared_list_crud.check_list_permission(db, list_id, current_user.id):
        raise HTTPException(status_code=403, detail="无权查看成员列表")
    
    members = shared_list_crud.get_list_members(db, list_id)
    return members