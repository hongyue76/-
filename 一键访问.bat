@echo off
chcp 65001 >nul
title 多用户待办事项系统 - 一键访问

echo ========================================
echo    多用户待办事项管理系统
echo        一键访问脚本
echo ========================================
echo.

:: 检查系统环境并自动选择最佳启动方式
echo 🔍 检测最佳访问方式...

:: 检查Docker是否可用
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 检测到Docker环境
    echo 🐳 将使用容器化部署方式
    
    :: 检查服务是否已在运行
    docker-compose ps | findstr "Up" >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ 服务已在运行
    ) else (
        echo 🚀 启动容器化服务...
        docker-compose up -d
        timeout /t 15 /nobreak >nul
    )
    
    set WEB_URL=http://localhost:8080
    set API_URL=http://localhost:8000/docs
    
) else (
    echo ⚠️  Docker不可用，使用本地开发模式
    echo 🚀 启动本地开发服务...
    
    :: 启动后端
    cd backend
    start "后端服务" cmd /k "python -m uvicorn app.main:app --reload --port 8000"
    timeout /t 3 /nobreak >nul
    
    :: 启动前端
    cd ..\frontend
    start "前端服务" cmd /k "npm run dev"
    timeout /t 3 /nobreak >nul
    
    cd ..
    set WEB_URL=http://localhost:5173
    set API_URL=http://localhost:8000/docs
)

echo.
echo ========================================
echo    系统准备就绪！
echo ========================================
echo.
echo 🌐 访问地址:
echo    应用界面: %WEB_URL%
echo    API文档:  %API_URL%
echo.
echo 📱 测试账号:
echo    用户名: testuser
echo    密码: password123
echo.
echo 💡 提示:
echo    - 正在为您自动打开浏览器...
echo    - 如未自动打开，请手动访问上述地址
echo.

:: 自动打开浏览器
timeout /t 2 /nobreak >nul
start "" "%WEB_URL%"

echo ✅ 浏览器已打开，Enjoy!
echo.
echo 按任意键退出...
pause >nul