from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class PriorityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ProgressStatusEnum(str, enum.Enum):
    TODO = "todo"           # 待开始
    IN_PROGRESS = "in_progress"  # 进行中
    REVIEW = "review"        # 审核中
    DONE = "done"            # 已完成

class AssignmentStatusEnum(str, enum.Enum):
    ASSIGNED = "assigned"      # 已分配
    ACCEPTED = "accepted"      # 已接受
    REJECTED = "rejected"      # 已拒绝
    COMPLETED = "completed"    # 已完成

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # 关系
    todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan")
    shared_lists = relationship("SharedList", back_populates="owner")

class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM)
    category = Column(String(50), default="默认")
    due_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 树形结构支持
    parent_id = Column(Integer, ForeignKey("todos.id"), nullable=True, index=True)
    
    # 离线同步相关字段
    version = Column(Integer, default=1, nullable=False)  # 版本号控制
    last_synced_at = Column(DateTime)  # 最后同步时间
    conflict_status = Column(String(20), default="resolved")  # 冲突状态
    conflict_details = Column(Text)  # 冲突详情JSON
    
    # 关系
    owner = relationship("User", back_populates="todos")
    comments = relationship("Comment", back_populates="todo", cascade="all, delete-orphan")
    assignments = relationship("TaskAssignment", back_populates="todo", cascade="all, delete-orphan")
    progress_tracks = relationship("ProgressTracking", back_populates="todo", cascade="all, delete-orphan")
    
    # 树形关系
    parent = relationship("Todo", remote_side=[id], back_populates="children")
    children = relationship("Todo", back_populates="parent")

class SharedList(Base):
    __tablename__ = "shared_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    owner = relationship("User", back_populates="shared_lists")
    members = relationship("SharedListMember", back_populates="shared_list", cascade="all, delete-orphan")

class SharedListMember(Base):
    __tablename__ = "shared_list_members"
    
    id = Column(Integer, primary_key=True, index=True)
    shared_list_id = Column(Integer, ForeignKey("shared_lists.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")  # owner, admin, member
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    shared_list = relationship("SharedList", back_populates="members")
    user = relationship("User")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    todo = relationship("Todo", back_populates="comments")
    user = relationship("User")

class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    assigner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 分配者
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 被分配者
    status = Column(Enum(AssignmentStatusEnum), default=AssignmentStatusEnum.ASSIGNED)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime)
    completed_at = Column(DateTime)
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)  # 拒绝原因
    
    # 关系
    todo = relationship("Todo")
    assigner = relationship("User", foreign_keys=[assigner_id])
    assignee = relationship("User", foreign_keys=[assignee_id])

class OfflineOperation(Base):
    __tablename__ = "offline_operations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    operation_type = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE
    field_name = Column(String(50))  # 修改的字段名
    old_value = Column(Text)  # 原始值
    new_value = Column(Text)  # 新值
    client_timestamp = Column(DateTime)  # 客户端时间戳（仅供参考）
    server_timestamp = Column(DateTime, default=datetime.utcnow)  # 服务器生成的时间戳
    logical_timestamp = Column(Integer)  # 逻辑时钟（用于严格排序）
    timestamp = Column(DateTime, default=datetime.utcnow)
    sequence_id = Column(String(50), unique=True)  # 唯一操作标识
    sync_status = Column(String(20), default="pending")  # pending, synced, conflicted
    device_id = Column(String(50))  # 设备标识
    
    # 关系
    user = relationship("User")
    todo = relationship("Todo")


class ProgressTracking(Base):
    __tablename__ = "progress_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 更新进度的用户
    status = Column(Enum(ProgressStatusEnum), default=ProgressStatusEnum.TODO)
    progress_percentage = Column(Integer, default=0)  # 进度百分比 0-100
    notes = Column(Text)  # 进度说明
    hours_spent = Column(Integer, default=0)  # 花费小时数
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    todo = relationship("Todo")
    user = relationship("User")