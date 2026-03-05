
#!/bin/bash
echo "🚀 启动生活助手AI Agent..."

# 启动后端
echo "📡 启动后端服务..."
cd backend
python app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 启动前端（使用Python简单HTTP服务器）
echo "🌐 启动前端服务..."
cd ../frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!

echo ""
echo "=" * 60
echo "✅ 服务已启动！"
echo "📡 后端地址: http://localhost:5000"
echo "🌐 前端地址: http://localhost:3000"
echo "=" * 60
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
wait $BACKEND_PID $FRONTEND_PID
