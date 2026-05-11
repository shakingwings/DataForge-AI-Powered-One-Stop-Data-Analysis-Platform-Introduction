#!/bin/bash
echo "========================================"
echo "  数据分析智能体 - 启动脚本"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/3] 启动后端服务..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "后端服务已启动 (PID: $BACKEND_PID)"

echo ""
echo "[2/3] 启动前端服务..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "前端服务已启动 (PID: $FRONTEND_PID)"

echo ""
echo "========================================"
echo "  服务已启动！"
echo "  前端地址: http://localhost:3000"
echo "  后端API: http://localhost:8000/docs"
echo "========================================"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
