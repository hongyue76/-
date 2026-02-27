# 多用户同步待办事项应用

## 项目概述

这是一个基于Vue 3 + FastAPI构建的企业级多用户待办事项管理应用，具有以下特性：

- ✅ 用户账户管理（注册、登录、JWT认证）
- ✅ 待办事项核心功能（增删改查、分类、优先级、截止日期）
- ✅ 团队协作功能（共享清单、任务分配、评论系统）
- ✅ 离线支持（本地存储、智能同步、冲突解决）
- ✅ 实时数据同步（WebSocket）
- ✅ 响应式UI设计
- ✅ Docker容器化部署

## 技术栈

### 前端
- Vue 3 + Composition API
- Vite 构建工具
- Pinia 状态管理
- Element Plus UI组件库
- Axios HTTP客户端
- Socket.IO Client WebSocket客户端

### 后端
- FastAPI Web框架
- SQLAlchemy ORM
- PostgreSQL 数据库
- Redis 缓存
- JWT 身份认证
- Pydantic 数据验证

### 部署
- Docker + Docker Compose
- Nginx 反向代理

## 快速开始

### 开发环境启动

1. 克隆项目
```bash
git clone <repository-url>
cd todo-app
```

2. 启动后端服务
```bash
cd backend
pip install -r requirements.txt
python run.py
```

3. 启动前端服务
```bash
cd frontend
npm install
npm run dev
```

### Docker部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 项目结构

```
todo-app/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模式
│   │   ├── crud/           # 数据操作
│   │   ├── core/           # 核心配置
│   │   └── utils/          # 工具函数
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile          # 后端Docker配置
│
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   ├── views/          # 页面视图
│   │   ├── stores/         # Pinia状态管理
│   │   ├── router/         # 路由配置
│   │   └── utils/          # 工具函数
│   ├── package.json        # Node.js依赖
│   └── Dockerfile          # 前端Docker配置
│
├── docker-compose.yml      # Docker编排文件
└── README.md              # 项目说明文档
```

## API接口

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

### 待办事项接口
- `GET /api/todos/` - 获取待办事项列表
- `POST /api/todos/` - 创建待办事项
- `GET /api/todos/{id}` - 获取特定待办事项
- `PUT /api/todos/{id}` - 更新待办事项
- `DELETE /api/todos/{id}` - 删除待办事项
- `GET /api/todos/category/{category}` - 按分类获取待办事项
- `GET /api/todos/stats/completion` - 获取完成统计

### WebSocket接口
- `WS /api/ws/sync/{user_id}` - 实时同步连接

## 环境变量配置

### 后端配置 (.env)
```env
DATABASE_URL=postgresql://postgres:password@localhost/todo_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_ORIGINS=["http://localhost:5173"]
```

## 开发指南

### 数据库迁移
```bash
# 初始化Alembic
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "initial migration"

# 执行迁移
alembic upgrade head
```

### 代码规范
- Python: 遵循PEP 8规范
- JavaScript: 使用ESLint和Prettier
- Vue: 遵循Vue官方风格指南

### 测试
```bash
# 后端测试
cd backend
python -m pytest tests/

# 前端测试
cd frontend
npm run test
```

## 部署说明

### 生产环境配置
1. 修改`.env`文件中的敏感配置
2. 设置强密码和密钥
3. 配置SSL证书
4. 调整Nginx配置优化性能

### 监控和日志
- 使用Docker日志驱动收集日志
- 配置健康检查端点
- 设置监控告警

### 功能演进历程

### 第一阶段 - MVP核心功能 ✓
- [x] 用户注册登录
- [x] 基础待办事项管理
- [x] 响应式UI界面
- [x] Docker部署

### 第二阶段 - 协作增强 ✓
- [x] 共享清单管理
- [x] 任务评论系统
- [x] 权限控制体系
- [x] 团队协作中心

### 第三阶段 - 离线支持 ✓
- [x] 本地数据存储
- [x] 智能同步机制
- [x] 网络状态监测
- [x] 冲突解决策略
- [x] 离线UI指示器

### 第四阶段 - 未来规划
- [ ] 实时通知系统
- [ ] 高级数据分析
- [ ] 移动端应用
- [ ] 第三方集成
- [ ] AI智能助手

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 许可证

MIT License