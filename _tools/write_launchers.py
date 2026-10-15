# -*- coding: utf-8 -*-
"""生成 start-all.bat / stop-all.bat。

为什么用脚本写而不是直接编辑：Write/heredoc 通道会把 bat 里的 `>nul` 改写成形如
`>/dev/null` 的内容，Windows 上直接报错。用 Python 显式写字节最稳。
"""
from pathlib import Path

ROOT = Path(r"D:/software/PycharmProjects/作品矩阵")

START = r'''@echo off
chcp 65001 >nul 2>&1
title 李奕波个人作品矩阵 - 全模块启动
cd /d "%~dp0"

echo ============================================================
echo   李奕波个人作品矩阵 · 全模块启动（由 _tools\supervisor.py 托管）
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
echo   P02 运营助手  boss@example.com / Test123456   （老板）
echo                 ops@example.com / Test123456    （运营）
echo                 design@example.com / Test123456 （美工）
echo                 cs@example.com / Test123456     （客服）
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
'''

STOP = r'''@echo off
chcp 65001 >nul 2>&1
title 李奕波个人作品矩阵 - 全模块停止
cd /d "%~dp0"

echo 停止全部服务（含手工启动、占用端口的旧进程）...
echo.
python -X utf8 _tools\supervisor.py stop --takeover %*
echo.
echo 完成。
pause >nul
'''


def write(name: str, body: str) -> None:
    path = ROOT / name
    # CRLF + 无 BOM：cmd.exe 对 LF-only 的批处理会解析异常
    path.write_bytes(body.replace("\n", "\r\n").encode("utf-8"))
    print("wrote", path, path.stat().st_size, "bytes")


if __name__ == "__main__":
    write("start-all.bat", START)
    write("stop-all.bat", STOP)
