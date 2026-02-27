from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api import auth, todos, users, websocket, shared_lists, comments, assignments, progress, subtasks, offline_sync
from app.core.config import settings
from app.core.database import engine, Base
import os

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="多用户同步待办事项应用API"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(todos.router, prefix="/api/todos", tags=["待办事项"])
app.include_router(subtasks.router, prefix="/api/subtasks", tags=["子任务"])
app.include_router(offline_sync.router, prefix="/api/offline", tags=["离线同步"])


app.include_router(shared_lists.router, prefix="/api", tags=["共享清单"])
app.include_router(comments.router, prefix="/api", tags=["评论"])
app.include_router(assignments.router, prefix="/api", tags=["任务分配"])
app.include_router(progress.router, prefix="/api", tags=["进度跟踪"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])

@app.get("/")
async def root():
    return {"message": "待办事项API服务正常运行"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/docs/local", response_class=HTMLResponse)
async def local_docs():
    """本地API文档页面"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "docs.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
        <head><title>API文档</title></head>
        <body>
            <h1>📝 待办事项API文档</h1>
            <p>本地文档文件未找到，请检查 templates/docs.html 文件</p>
            <a href="/docs">使用Swagger UI</a>
        </body>
        </html>
        """)