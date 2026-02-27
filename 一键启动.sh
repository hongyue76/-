#!/bin/bash

# 多用户待办事项系统 - 一键启动脚本

echo "========================================"
echo "   多用户待办事项管理系统"
echo "        一键启动脚本"
echo "========================================"
echo ""

# 检查是否在正确目录
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    echo "当前目录: $(pwd)"
    exit 1
fi

echo "✅ 检测到项目文件"

# 检查Python环境
echo "🔍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python，请先安装Python 3.8+"
    exit 1
fi
echo "✅ Python环境正常"

# 检查Node.js环境
echo "🔍 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo "❌ 未找到Node.js，请先安装Node.js 16+"
    exit 1
fi
echo "✅ Node.js环境正常"

# 启动后端服务
echo "🚀 启动后端服务..."
cd backend
python3 -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
sleep 3

# 启动前端服务
echo "🚀 启动前端服务..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
sleep 3

# 返回项目根目录
cd ..

# 显示访问信息
echo ""
echo "========================================"
echo "   系统启动完成！"
echo "========================================"
echo ""
echo "🌐 访问地址:"
echo "   前端界面: http://localhost:5173"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo "📱 测试账号:"
echo "   用户名: testuser"
echo "   密码: password123"
echo ""
echo "💡 提示:"
echo "   - 后端进程PID: $BACKEND_PID"
echo "   - 前端进程PID: $FRONTEND_PID"
echo "   - 使用 'kill $BACKEND_PID $FRONTEND_PID' 停止服务"
echo "   - 或按 Ctrl+C 停止此脚本"
echo ""

# 等待用户输入
read -p "按回车键打开浏览器访问系统..." dummy

# 自动打开浏览器 (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:5173"
# Linux
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "http://localhost:5173"
fi

echo "系统已启动，Enjoy!"

# 保持脚本运行
wait