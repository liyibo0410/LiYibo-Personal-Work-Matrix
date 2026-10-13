@echo off
chcp 65001 >nul 2>&1
title CloudPivot P08 - 直播切片
cd /d "%~dp0"
echo ============================================================
echo   CloudPivot P08 - 直播切片系统
echo   http://127.0.0.1:8080
echo   [MOCK] ASR/评分/视频处理均为模拟
echo ============================================================
uv run python app/main.py
pause
