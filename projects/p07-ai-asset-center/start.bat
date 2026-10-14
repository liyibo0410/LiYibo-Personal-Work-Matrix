@echo off
chcp 65001 >nul 2>&1
title P07 AI 素材中心
cd /d "%~dp0"
echo ============================================================
echo   CloudPivot P07 - AI 素材中心
echo   http://127.0.0.1:8070
echo   [边界] 图片为程序化规格卡(非AI出图); 无Key时打标/文案退回规则并标注
echo ============================================================
uv run python app/main.py
pause
