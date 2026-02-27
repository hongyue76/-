from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 项目基本信息
    PROJECT_NAME: str = "待办事项应用"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./todo_app.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # WebSocket配置
    WEBSOCKET_MAX_CONNECTIONS: int = 1000
    
    class Config:
        env_file = ".env"

settings = Settings()