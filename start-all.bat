@echo off
chcp 65001 >nul 2>&1
title 云枢智能 - 全模块启动
cd /d "%~dp0"

echo ============================================================
echo   云枢智能 · 全模块启动（由 _tools\supervisor.py 托管）
echo   日志：_runtime\logs\^<服务^>.log   PID：_runtime\pids\
echo ============================================================
echo.

REM 不带参数 = 启动全部；带 id = 只起指定服务，例如 start-all.bat p04 p07
python -X utf8 _tools\supervisor.py start %*
if errorlevel 1 goto fail

echo.
echo ============================================================
echo   统一入口   http://127.0.0.1:8800   （勿用 file:// 打开）
echo.
echo   外壳演示账号  owner/owner123  ops/ops123  legal/legal123
echo                 sales/sales123  admin/admin123
echo   P02 运营助手  boss@cloudpivot.com / Test123456   （老板）
echo                 ops@cloudpivot.com / Test123456    （运营）
echo                 design@cloudpivot.com / Test123456 （美工）
echo                 cs@cloudpivot.com / Test123456     （客服）
echo   P05 合同审批  legal/Legal@2026  applicant/Apply@2026  admin/Admin@2026
echo.
echo   查看状态   python _tools\supervisor.py status
echo   停止全部   stop-all.bat
echo ============================================================
pause >nul
exit /b 0

:fail
echo.
echo 有服务没起来，看上面的 [超时] 行与 _runtime\logs\ 下对应日志。
pause >nul
exit /b 1
