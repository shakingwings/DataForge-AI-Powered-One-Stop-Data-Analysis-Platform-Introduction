@echo off
chcp 65001 >nul 2>&1

echo ========================================
echo   Data Analysis Agent - Starting...
echo ========================================
echo.

set "ROOT=%~dp0"

echo [1/3] Starting backend server...
start "Backend" "%ROOT%backend\run.bat"
echo     Backend: http://localhost:8000

echo [2/3] Starting frontend server...
start "Frontend" "%ROOT%frontend\run.bat"
echo     Frontend: http://localhost:3000

echo [3/3] Waiting 10 seconds for services...
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo   All services started!
echo   Frontend: http://localhost:3000
echo   Backend API docs: http://localhost:8000/docs
echo ========================================
echo.

start http://localhost:3000
pause
