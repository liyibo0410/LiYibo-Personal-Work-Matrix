@echo off
chcp 65001 >nul 2>&1
title P06 Data Platform - CloudPivot
echo ============================================
echo   P06 数据中台 - CloudPivot
echo   Port: 8060
echo ============================================
echo.

cd /d "%~dp0"

REM Check for uv
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Installing dependencies with uv...
    uv sync
    echo [INFO] Starting server...
    uv run python app/main.py
) else (
    echo [WARN] uv not found, using system Python...
    pip install -e . >nul 2>&1
    python app/main.py
)

pause
