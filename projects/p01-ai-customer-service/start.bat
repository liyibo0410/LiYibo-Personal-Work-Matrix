@echo off
chcp 65001 >nul
title P01 AI Customer Service - Li Yibo's Personal Portfolio
cd /d "%~dp0"

echo ============================================================
echo   P01 AI Customer Service Backend
echo   Li Yibo's Personal Portfolio Platform
echo ============================================================
echo.

REM Check and free port 18082
echo [1/2] Checking port 18082...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :18082 ^| findstr LISTENING 2^>nul') do (
    echo   Port 18082 is occupied (PID: %%a), stopping...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] Cannot stop process %%a
    ) else (
        echo   [OK] Process stopped
    )
)
echo   [OK] Port check done
echo.

REM Start service
echo [2/2] Starting backend service...
echo ============================================================
echo   Service started successfully!
echo   API URL:    http://localhost:18082
echo   API Docs:   http://localhost:18082/docs
echo   Frontend:   http://localhost:5173
echo ============================================================
echo.
echo Press Ctrl+C to stop the service
echo.

uv run python main.py

echo.
echo ============================================================
echo   Service stopped
echo ============================================================
pause
