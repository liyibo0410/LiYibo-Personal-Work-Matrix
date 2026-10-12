@echo off
chcp 936 >nul
title BOSS 智库
cd /d "%~dp0"

echo ============================================================
echo   BOSS 智库 - 一键启动
echo ============================================================
echo.
echo.
echo   控制台地址: http://localhost:8100/console.html
echo.
echo   按 Ctrl+C 停止服务
echo.
echo ============================================================
echo.

python -m uvicorn web.api.console_service:app --port 8100 --reload

echo.
echo 服务已停止
pause
