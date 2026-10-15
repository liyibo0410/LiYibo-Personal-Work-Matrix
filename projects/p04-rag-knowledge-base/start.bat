@echo off
chcp 65001 >nul 2>&1
title Li Yibo's Personal Portfolio P04 - RAG 知识库
cd /d "%~dp0"

echo ============================================================
echo   RAG 知识库 - 一键启动
echo ============================================================
echo.
echo   控制台地址: http://localhost:8041/console.html
echo.
echo   按 Ctrl+C 停止服务
echo.
echo ============================================================
echo.

uv run python -m uvicorn web.api.console_service:app --port 8041 --reload

echo.
echo 服务已停止
pause
