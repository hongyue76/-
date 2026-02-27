@echo off
chcp 65001 >nul
title 多用户待办事项系统 - 一键启动

echo ========================================
echo    多用户待办事项管理系统
echo         一键启动脚本
echo ========================================
echo.

:: 检查是否在正确目录
if not exist "backend\app\main.py" (
    echo ❌ 错误: 请在项目根目录运行此脚本
    echo 当前目录: %cd%
    pause
    exit /b 1
)

echo ✅ 检测到项目文件

:: 检查Python环境
echo 🔍 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python环境正常

:: 检查Node.js环境
echo 🔍 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Node.js，请先安装Node.js 16+
    pause
    exit /b 1
)
echo ✅ Node.js环境正常

:: 启动后端服务
echo 🚀 启动后端服务...
cd backend
start "后端服务" cmd /k "python -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul

:: 启动前端服务
echo 🚀 启动前端服务...
cd ..\frontend
start "前端服务" cmd /k "npm run dev"
timeout /t 3 /nobreak >nul

:: 返回项目根目录
cd ..

:: 显示访问信息
echo.
echo ========================================
echo    系统启动完成！
echo ========================================
echo.
echo 🌐 访问地址:
echo    前端界面: http://localhost:5173
echo    后端API:  http://localhost:8000
echo    API文档:  http://localhost:8000/docs
echo.
echo 📱 测试账号:
echo    用户名: testuser
echo    密码: password123
echo.
echo 💡 提示:
echo    - 按 Ctrl+C 可停止各服务窗口
echo    - 关闭此窗口不会影响服务运行
echo    - 如需重新启动，请关闭所有服务窗口后重新运行此脚本
echo.
echo 按任意键打开浏览器访问系统...
pause >nul

:: 自动打开浏览器
start "" "http://localhost:5173"

echo 系统已启动，Enjoy!