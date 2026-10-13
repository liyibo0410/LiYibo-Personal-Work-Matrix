@echo off
chcp 65001 >nul 2>&1
title P07 AI 素材中心
cd /d "%~dp0"
echo ============================================================
echo   CloudPivot P07 - AI 素材中心
echo   http://127.0.0.1:8070
echo   [MOCK] 搜索/生成为模拟实现
echo ============================================================
uv run python app/main.py
pause
