@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================================
echo   Li Yibo's Personal Portfolio P09 - AI 销售考核
echo   http://localhost:8090
echo   [MOCK] LLM scoring is rule-based
echo ============================================================
uv run python app/main.py
pause
