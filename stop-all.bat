@echo off
chcp 65001 >nul 2>&1
title 云枢智能 - 全模块停止
cd /d "%~dp0"

echo 停止全部服务（含手工启动、占用端口的旧进程）...
echo.
python -X utf8 _tools\supervisor.py stop --takeover %*
echo.
echo 完成。
pause >nul
