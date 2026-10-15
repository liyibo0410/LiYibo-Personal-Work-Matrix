@echo off
chcp 65001 >nul 2>&1
title Li Yibo's Personal Portfolio P05 - 衡鉴合同审查
cd /d "%~dp0"

echo ============================================================
echo   衡鉴 Contract Review System V2.1.9
echo   http://127.0.0.1:8770
echo   零第三方依赖 · 纯 Python 标准库
echo ============================================================
echo.

python run.py

echo.
echo 服务已停止
pause
