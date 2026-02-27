# 团队协作功能扩展文档

## 功能概述

本次扩展为待办事项应用增加了完整的团队协作功能，包括共享清单管理、任务分配和评论系统。

## 新增功能模块

### 1. 共享清单管理
- **创建共享清单**：用户可以创建可共享的任务清单
- **成员管理**：添加/移除成员，设置成员角色（所有者、管理员、成员）
- **权限控制**：基于角色的访问控制
- **清单分类**：区分我创建的清单和我参与的清单

### 2. 评论系统
- **任务评论**：为每个待办事项添加评论
- **实时交互**：支持评论的增删改查
- **用户标识**：显示评论作者和时间
- **权限控制**：用户只能编辑/删除自己的评论

### 3. 协作中心界面
- **统一入口**：集中的协作功能管理面板
- **功能导航**：清晰的功能分类导航
- **响应式设计**：适配不同屏幕尺寸

## 技术实现

### 后端扩展

#### 新增数据模型
```python
# 共享清单模型
class SharedList(Base):
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100))
    description = Column(Text)
    members = relationship("SharedListMember")

# 清单成员模型
class SharedListMember(Base):
    id = Column(Integer, primary_key=True)
    shared_list_id = Column(Integer, ForeignKey("shared_lists.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20))  # owner, admin, member

# 评论模型
class Comment(Base):
    id = Column(Integer, primary_key=True)
    todo_id = Column(Integer, ForeignKey("todos.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
```

#### 新增API接口

**共享清单API** (`/api/shared-lists/`)
- `POST /` - 创建共享清单
- `GET /` - 获取我创建的清单
- `GET /member` - 获取我参与的清单
- `PUT /{list_id}` - 更新清单信息
- `DELETE /{list_id}` - 删除清单
- `POST /{list_id}/members/{user_id}` - 添加成员
- `DELETE /{list_id}/members/{user_id}` - 移除成员
- `PUT /{list_id}/members/{user_id}/role` - 更新成员角色
- `GET /{list_id}/members` - 获取清单成员

**评论API** (`/api/comments/`)
- `POST /todos/{todo_id}` - 为任务添加评论
- `GET /todos/{todo_id}` - 获取任务评论
- `PUT /{comment_id}` - 更新评论
- `DELETE /{comment_id}` - 删除评论

#### 权限控制机制
- **角色等级**：owner(3) > admin(2) > member(1)
- **操作权限**：
  - Owner：完全控制，可删除清单，修改任何成员角色
  - Admin：可管理成员，修改清单信息
  - Member：基本查看和操作权限

### 前端扩展

#### 新增状态管理
```javascript
// 共享清单状态管理
const useSharedListsStore = defineStore('sharedLists', () => {
  const sharedLists = ref([])
  const myLists = ref([])
  // CRUD操作方法...
})

// 评论状态管理
const useCommentsStore = defineStore('comments', () => {
  const comments = ref({})
  // 评论相关操作...
})
```

#### 新增组件
- `SharedListsManager.vue` - 共享清单管理组件
- `CommentsSection.vue` - 评论功能组件
- `CollaborationView.vue` - 协作中心主页面

#### 路由更新
新增 `/collaboration` 路由指向协作中心页面

## 数据库变更

### 新增表结构
```sql
-- 共享清单表
CREATE TABLE shared_lists (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 清单成员表
CREATE TABLE shared_list_members (
    id SERIAL PRIMARY KEY,
    shared_list_id INTEGER REFERENCES shared_lists(id),
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 评论表
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    todo_id INTEGER REFERENCES todos(id),
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 安全考虑

### 访问控制
- 所有协作相关API都需要JWT认证
- 基于成员关系的资源访问控制
- 操作权限验证（创建者、管理员、普通成员）

### 数据保护
- 敏感操作需要二次确认
- 用户只能访问自己相关的数据
- 完整的操作日志记录

## 使用指南

### 共享清单使用流程
1. 进入"协作中心" → "共享清单"
2. 点击"创建共享清单"
3. 输入清单名称和描述
4. 在成员管理中添加团队成员
5. 设置成员角色权限

### 评论功能使用
1. 在待办事项详情页找到评论区域
2. 点击"添加评论"输入内容
3. 可随时编辑或删除自己的评论
4. 实时查看其他成员的评论

## 后续扩展方向

### 即将实现的功能
- [ ] 任务分配功能
- [ ] 实时通知系统
- [ ] 团队活动动态
- [ ] 协作数据分析
- [ ] 文件附件支持
- [ ] 标签和筛选功能

### 性能优化
- [ ] 评论分页加载
- [ ] WebSocket实时推送
- [ ] 数据缓存优化
- [ ] 图片压缩处理

## 部署说明

### 环境要求
- Node.js >= 16.0
- Python >= 3.8
- PostgreSQL >= 12.0
- Redis >= 6.0

### 启动步骤
```bash
# 后端服务
cd backend
pip install -r requirements.txt
python run.py

# 前端服务
cd frontend
npm install
npm run dev

# 或使用Docker
docker-compose up -d
```

## API文档

详细的API接口文档可通过访问 `/docs` 端点查看Swagger UI界面。