@echo off
chcp 936 >nul
title Ecommerce Operation Assistant
cd /d "%~dp0"

echo ============================================================
echo   电商运营助手 - 一键启动
echo ============================================================
echo.

REM 检查并清理端口 8000
echo [1/4] 检查后端端口...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo   发现端口 8000 被占用 (PID: %%a)，正在停止...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] 无法停止进程 %%a
    ) else (
        echo   [OK] 已停止旧进程
    )
)
echo   [OK] 端口 8000 可用
echo.

REM 检查并清理端口 3000
echo [2/4] 检查前端端口...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    echo   发现端口 3000 被占用 (PID: %%a)，正在停止...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] 无法停止进程 %%a
    ) else (
        echo   [OK] 已停止旧进程
    )
)
echo   [OK] 端口 3000 可用
echo.

REM 启动 Docker 基础设施
echo [3/4] 启动 Docker 基础设施...
docker compose --env-file .env up -d >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Docker 启动失败，请确保 Docker Desktop 正在运行
) else (
    echo   [OK] Docker 服务已启动
    timeout /t 5 /nobreak >nul
)
echo.

REM 启动应用服务
echo [4/4] 启动应用服务...
start "Backend" /d "%~dp0api" cmd /k "uv run uvicorn app.main:app --reload --port 8000"
start "Frontend" /d "%~dp0web" cmd /k "npm run dev"

echo.
echo ============================================================
echo   启动成功!
echo   后端 API: http://localhost:8000/docs
echo   前端界面: http://localhost:3000
echo ============================================================
echo.
echo 按任意键关闭此窗口 (服务会继续运行)
pause >nul
