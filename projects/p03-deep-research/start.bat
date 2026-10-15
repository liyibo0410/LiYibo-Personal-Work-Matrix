@echo off
chcp 65001 >nul 2>&1
title Li Yibo's Personal Portfolio P03 - NL2SQL 问数
cd /d "%~dp0"

echo ============================================================
echo   Li Yibo's Personal Portfolio P03 - NL2SQL 问数系统
echo ============================================================
echo.

REM 检查并释放端口 8030
echo [1/2] 检查后端端口...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8030 ^| findstr LISTENING 2^>nul') do (
    echo   发现端口 8030 被占用 (PID: %%a)，正在停止...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] 无法停止进程 %%a
    ) else (
        echo   [OK] 已停止进程
    )
)
echo   [OK] 端口 8030 可用
echo.

REM 启动服务
echo [2/2] 启动服务...
start "P03-Backend" /d "%~dp0" cmd /k "uv run python main.py"

echo.
echo ============================================================
echo   启动成功!
echo   后端 API: http://localhost:8030
echo ============================================================
echo.
echo 按任意键关闭此窗口 (不影响服务运行)
pause >nul
