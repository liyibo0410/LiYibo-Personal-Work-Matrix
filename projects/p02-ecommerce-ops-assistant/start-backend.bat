@echo off
chcp 65001 >nul
title Ecommerce Assistant - Backend (API :8000)
cd /d "%~dp0api"
echo [backend] Starting FastAPI on http://127.0.0.1:8000 ...
echo [backend] Swagger: http://127.0.0.1:8000/docs
echo.
".venv\Scripts\python.exe" scripts\run_local_dev.py
echo.
echo [backend] Stopped. Press any key to close.
pause >nul
