@echo off
setlocal

echo [INFO] 启动待办事项应用...

REM 检查Docker是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 请先安装Docker Desktop
    pause
    exit /b 1
)

REM 检查Docker Compose是否安装
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 请先安装Docker Compose
    pause
    exit /b 1
)

REM 构建并启动服务
echo [BUILD] 构建Docker镜像...
docker-compose build

echo [START] 启动所有服务...
docker-compose up -d

echo [WAIT] 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo [STATUS] 服务状态:
docker-compose ps

echo [SUCCESS] 应用启动完成!
echo [WEB] 前端访问地址: http://localhost:8080
echo [API] API文档地址: http://localhost:8000/docs
echo.
echo [ADMIN] 管理命令:
echo   查看日志: docker-compose logs -f
echo   停止服务: docker-compose down
echo   重启服务: docker-compose restart

pause