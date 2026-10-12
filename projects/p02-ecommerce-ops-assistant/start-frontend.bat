@echo off
chcp 65001 >nul
title Ecommerce Assistant - Frontend (Web :3000)
cd /d "%~dp0web"
echo [frontend] Starting Next.js on http://localhost:3000 ...
echo.
call npm run dev
echo.
echo [frontend] Stopped. Press any key to close.
pause >nul
