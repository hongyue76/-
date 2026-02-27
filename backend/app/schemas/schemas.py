from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from app.models.models import PriorityEnum, ProgressStatusEnum, AssignmentStatusEnum

# 用户相关模式
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

# 待办事项相关模式
class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    category: str = "默认"
    due_date: Optional[datetime] = None
    parent_id: Optional[int] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None

class TodoResponse(TodoBase):
    id: int
    user_id: int
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[int] = None
    has_children: Optional[bool] = None
    children_count: Optional[int] = None
    # 离线同步字段
    version: int = 1
    last_synced_at: Optional[datetime] = None
    conflict_status: str = "resolved"
    
    class Config:
        from_attributes = True

# 共享清单相关模式
class SharedListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class SharedListCreate(SharedListBase):
    pass

class SharedListResponse(SharedListBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 评论相关模式
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1)

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: int
    todo_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 认证相关模式
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None

# 任务分配相关模式
class TaskAssignmentBase(BaseModel):
    todo_id: int
    assignee_id: int
    
class TaskAssignmentCreate(TaskAssignmentBase):
    pass

class TaskAssignmentUpdate(BaseModel):
    status: Optional[AssignmentStatusEnum] = None
    rejection_reason: Optional[str] = None

class TaskAssignmentResponse(TaskAssignmentBase):
    id: int
    assigner_id: int
    status: AssignmentStatusEnum
    assigned_at: datetime
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True

# 进度跟踪相关模式
class ProgressTrackingBase(BaseModel):
    todo_id: int
    status: ProgressStatusEnum = ProgressStatusEnum.TODO
    progress_percentage: int = Field(0, ge=0, le=100)
    notes: Optional[str] = None
    hours_spent: int = Field(0, ge=0)
    
class ProgressTrackingCreate(ProgressTrackingBase):
    pass

class ProgressTrackingUpdate(BaseModel):
    status: Optional[ProgressStatusEnum] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    hours_spent: Optional[int] = Field(None, ge=0)

class ProgressTrackingResponse(ProgressTrackingBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# WebSocket消息模式
class WebSocketMessage(BaseModel):
    type: str  # sync, update, delete, comment
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 离线操作相关模式
class OfflineOperationBase(BaseModel):
    todo_id: int
    operation_type: str  # CREATE, UPDATE, DELETE
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    device_id: Optional[str] = None


class OfflineOperationCreate(OfflineOperationBase):
    pass


class OfflineOperationResponse(OfflineOperationBase):
    id: int
    user_id: int
    timestamp: datetime
    sequence_id: str
    sync_status: str
    
    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    last_sync_time: Optional[datetime] = None
    device_id: str
    pending_operations: List[OfflineOperationCreate] = []


class ConflictResolution(BaseModel):
    operation_id: int
    resolution: str  # accept_client, accept_server, merge, auto_merge
    merged_data: Optional[dict] = None
    conflict_strategy: Optional[str] = None  # server_wins, client_wins, smart_merge


class SyncResponse(BaseModel):
    server_updates: List[TodoResponse]
    conflicts: List[dict]
    sync_timestamp: datetime
    has_more: bool


# 子任务相关模式
class SubtaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    due_date: Optional[datetime] = None

class SubtaskMove(BaseModel):
    new_parent_id: Optional[int] = None  # None表示移动到根级别
    
class TodoTreeResponse(TodoResponse):
    children: List['TodoTreeResponse'] = []
    
    class Config:
        from_attributes = True