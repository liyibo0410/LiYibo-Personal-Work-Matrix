@echo off
chcp 65001 >nul 2>&1
title P10 模型微调平台
cd /d "%~dp0"
echo ============================================================
echo   CloudPivot P10 - 模型微调平台
echo   http://127.0.0.1:8101
echo   [MOCK] 训练/评测/部署均为模拟
echo ============================================================
uv run python app/main.py
pause
