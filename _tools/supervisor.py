#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""李奕波个人作品矩阵全平台服务管理器。

start-all.bat 的老办法是开十几个独立控制台窗口：看不见日志、关窗口就断、
端口起了没有也没人核对。这里改成分离进程 + 落盘日志 + PID 记录，并在使用前
用 TCP 探测确认端口真的在监听。

用法：
  python _tools/supervisor.py status              # 看全平台端口状态
  python _tools/supervisor.py start               # 启动全部（已在跑的跳过）
  python _tools/supervisor.py start p04 p07       # 只起指定服务
  python _tools/supervisor.py restart p01-web     # 重启单个服务
  python _tools/supervisor.py stop                # 停掉全部由本管理器托管的服务

端口一律从 shared/config/services.json 解析，不在本文件里重复定义。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "_runtime"
LOG_DIR = RUNTIME / "logs"
PID_DIR = RUNTIME / "pids"
REGISTRY = ROOT / "shared" / "config" / "services.json"
IS_WIN = os.name == "nt"


def registry() -> dict:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data["services"]


def port_of(services: dict, key: str, field: str = "web_port") -> int:
    svc = services[key]
    return int(svc.get(field) or svc["api_port"])


def build_catalog(services: dict) -> list[dict]:
    """服务清单。cwd 相对仓库根，cmd 里的 {port} 由注册表填充。"""
    p = lambda key, field="web_port": port_of(services, key, field)
    commerce = int(services["p01"].get("commerce_port", 18081))
    return [
        {
            "id": "shell", "label": "统一外壳网关",
            "cwd": "shell", "ports": [8800],
            "cmd": '{python} serve.py',
        },
        # P01 三段：商城中台(18081) → AI 后端(18082) → 前端(5173)。
        # 中台不起，前端右侧就会报「加载订单列表失败」。
        {
            "id": "p01-commerce", "label": "P01 商城中台",
            "cwd": "projects/p01-ai-customer-service/external/ecommerce-service-backend",
            "ports": [commerce], "venv_python": True,
            "cmd": '{python} main.py',
        },
        {
            "id": "p01-api", "label": "P01 AI 客服后端",
            "cwd": "projects/p01-ai-customer-service",
            "ports": [int(services["p01"]["api_port"])],
            "cmd": 'uv run python main.py',
        },
        {
            "id": "p01-web", "label": "P01 AI 客服前端",
            "cwd": "projects/p01-ai-customer-service/external/customer-service-frontend",
            "ports": [p("p01")],
            "cmd": 'npm run dev',
        },
        {
            "id": "p02-api", "label": "P02 运营助手后端",
            "cwd": "projects/p02-ecommerce-ops-assistant/api",
            "ports": [int(services["p02"]["api_port"])],
            "venv_python": True, "cmd": '{python} scripts/run_local_dev.py',
        },
        {
            "id": "p02-web", "label": "P02 运营助手前端",
            "cwd": "projects/p02-ecommerce-ops-assistant/web",
            "ports": [p("p02")],
            "cmd": 'npm run dev -- -p {port}',
            "port_arg": p("p02"),
        },
        {
            "id": "p03-api", "label": "P03 NL2SQL 问数 后端",
            "cwd": "projects/p03-deep-research",
            "ports": [int(services["p03"]["api_port"])],
            "cmd": 'uv run python main.py',
        },
        {
            "id": "p03-web", "label": "P03 NL2SQL 问数 前端",
            "cwd": "projects/p03-deep-research/ui",
            "ports": [p("p03")],
            "cmd": 'npm run dev',
        },
        {
            "id": "p04", "label": "P04 RAG 知识库",
            "cwd": "projects/p04-rag-knowledge-base",
            "ports": [p("p04")], "venv_python": True,
            "cmd": '{python} -m uvicorn web.api.console_service:app --host 0.0.0.0 --port {port}',
            "port_arg": p("p04"),
        },
        {
            "id": "p05", "label": "P05 合同审批",
            "cwd": "projects/p05-contract-review",
            "ports": [p("p05")], "venv_python": True,
            "cmd": '{python} run.py',
        },
        {
            "id": "p06", "label": "P06 数据中台",
            "cwd": "projects/p06-data-platform",
            "ports": [p("p06")],
            "cmd": 'uv run python app/main.py',
        },
        {
            "id": "p07", "label": "P07 AI 素材中心",
            "cwd": "projects/p07-ai-asset-center",
            "ports": [p("p07")],
            "cmd": 'uv run python app/main.py',
        },
        {
            "id": "p08", "label": "P08 直播切片",
            "cwd": "projects/p08-live-clip",
            "ports": [p("p08")],
            "cmd": 'uv run python app/main.py',
        },
        {
            "id": "p09", "label": "P09 AI 销售考核",
            "cwd": "projects/p09-ai-sales-assessment",
            "ports": [p("p09")],
            "cmd": 'uv run python app/main.py',
        },
        {
            "id": "p10", "label": "P10 模型微调平台",
            "cwd": "projects/p10-model-finetune",
            "ports": [p("p10")],
            "cmd": 'uv run python app/main.py',
        },
    ]


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def pids_on_port(port: int) -> list[int]:
    """从 netstat 取监听该端口的 PID。输出按字节取回再解码 —— 中文 Windows 上
    netstat 是 GBK，用 text=True 会 UnicodeDecodeError。"""
    if not IS_WIN:
        return []
    raw = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True).stdout or b""
    out: list[int] = []
    for line in raw.decode("gbk", "replace").splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING":
            if cols[1].rsplit(":", 1)[-1] == str(port):
                try:
                    pid = int(cols[4])
                except ValueError:
                    continue
                if pid not in out:
                    out.append(pid)
    return out


def pid_file(sid: str) -> Path:
    return PID_DIR / f"{sid}.pid"


def managed_pid(sid: str) -> int | None:
    f = pid_file(sid)
    if not f.exists():
        return None
    try:
        return int(f.read_text().strip())
    except ValueError:
        return None


def resolve_python(entry: dict) -> str:
    """venv_python 的服务用自带虚拟环境，避免 uv/全局解释器漂移。"""
    cwd = ROOT / entry["cwd"]
    if entry.get("venv_python"):
        for cand in (cwd / ".venv" / "Scripts" / "python.exe", cwd / ".venv" / "bin" / "python"):
            if cand.exists():
                return str(cand)
    # 桌面应用走 pythonw 进来，服务却要用 python.exe：控制台子系统 + CREATE_NO_WINDOW
    # 才有那个隐藏 conhost，崩溃 traceback 能稳稳落到日志；pythonw 是 GUI 子系统，
    # 标志位不参与，异常可能只剩一个看不见的死进程。
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        console = exe.with_name("python.exe")
        if console.exists():
            return str(console)
    return sys.executable


def render_cmd(entry: dict) -> str:
    port = entry.get("port_arg") or (entry["ports"][0] if entry["ports"] else 0)
    return entry["cmd"].format(python=resolve_python(entry), port=port)


def spawn(entry: dict) -> subprocess.Popen:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    cwd = ROOT / entry["cwd"]
    cmd = render_cmd(entry)
    log = open(LOG_DIR / f"{entry['id']}.log", "ab", buffering=0)
    log.write(b"\n===== %s  %s =====\n" % (time.strftime("%Y-%m-%d %H:%M:%S").encode(), cmd.encode("utf-8", "replace")))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    flags = 0
    if IS_WIN:
        # 必须用 CREATE_NO_WINDOW，不能用 DETACHED_PROCESS。
        # 本机 Win11「默认终端 = Windows Terminal」会在 DETACHED_PROCESS 下照样
        # 给每个服务接管出一个可见窗口（实测 10 个服务 → 11 个窗口）；
        # CREATE_NO_WINDOW 走隐藏 conhost，不参与默认终端接管，且子进程有独立
        # 控制台 —— 父脚本退出后服务照样活着。
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        # 必须传字符串：传 list 时 list2cmdline 会把引号转成 \"，cmd.exe 不认。
        proc = subprocess.Popen(f'cmd /c {cmd}', cwd=str(cwd), shell=False,
                                creationflags=flags, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env)
    else:
        proc = subprocess.Popen(cmd, cwd=str(cwd), shell=True, start_new_session=True,
                                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=env)
    pid_file(entry["id"]).write_text(str(proc.pid))
    return proc


def stop_entry(entry: dict, takeover: bool = False) -> list[str]:
    """停服务。takeover=True 时连端口上的既有进程一起收（用于接管手工启动的服务）。"""
    notes: list[str] = []
    targets: set[int] = set()
    pid = managed_pid(entry["id"])
    if pid:
        targets.add(pid)
    if takeover:
        for port in entry["ports"]:
            targets.update(pids_on_port(port))
    for t in targets:
        if IS_WIN:
            # /T 杀进程树：cmd /c 包了一层，只杀父会留下真正的服务。
            subprocess.run(["taskkill", "/PID", str(t), "/T", "/F"], capture_output=True)
            notes.append(f"killed pid={t}")
        else:
            subprocess.run(["kill", str(t)], capture_output=True)
            notes.append(f"kill pid={t}")
    pf = pid_file(entry["id"])
    if pf.exists():
        pf.unlink()
    return notes


def wait_ports(entry: dict, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(port_open(pt) for pt in entry["ports"]):
            return True
        time.sleep(0.5)
    return all(port_open(pt) for pt in entry["ports"])


def cmd_status(catalog: list[dict], verbose: bool = False) -> int:
    print(f"{'服务':<14} {'端口':<12} {'状态':<8} 说明")
    print("-" * 68)
    up = 0
    for e in catalog:
        ports = ",".join(str(x) for x in e["ports"])
        live = all(port_open(x) for x in e["ports"])
        up += live
        mark = "在线" if live else "未启动"
        print(f"{e['id']:<14} {ports:<12} {mark:<8} {e['label']}")
        if verbose and not live:
            log = LOG_DIR / f"{e['id']}.log"
            if log.exists():
                tail = log.read_bytes()[-600:].decode("utf-8", "replace").strip().splitlines()[-6:]
                for t in tail:
                    print(f"{'':<14}   ! {t}")
    print("-" * 68)
    print(f"{up}/{len(catalog)} 在线")
    return 0 if up == len(catalog) else 1


def cmd_start(catalog: list[dict], targets: list[str], takeover: bool) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    picked = [e for e in catalog if not targets or e["id"] in targets]
    for e in picked:
        if all(port_open(x) for x in e["ports"]):
            if not takeover:
                print(f"[跳过] {e['id']:<13} 端口 {e['ports']} 已在监听")
                continue
            for note in stop_entry(e, takeover=True):
                print(f"[接管] {e['id']:<13} {note}")
            time.sleep(1.2)
        cwd = ROOT / e["cwd"]
        if not cwd.is_dir():
            print(f"[失败] {e['id']:<13} 目录不存在 {cwd}")
            continue
        spawn(e)
        print(f"[启动] {e['id']:<13} {render_cmd(e)}")
    # 统一等待：npm/vite 首次冷启动要几十秒，逐个等会串行拖时间。
    pending = [e for e in picked if not all(port_open(x) for x in e["ports"])]
    if pending:
        print(f"\n等待 {len(pending)} 个服务就绪（最长 120 秒）...")
        deadline = time.time() + 120
        done: set[str] = set()
        while time.time() < deadline and len(done) < len(pending):
            for e in pending:
                if e["id"] in done:
                    continue
                if all(port_open(x) for x in e["ports"]):
                    done.add(e["id"])
                    print(f"[就绪] {e['id']:<13} {','.join(map(str, e['ports']))}")
            time.sleep(1.0)
        for e in pending:
            if e["id"] not in done:
                print(f"[超时] {e['id']:<13} 未监听 {e['ports']} —— 日志 _runtime/logs/{e['id']}.log")
                log = LOG_DIR / f"{e['id']}.log"
                if log.exists():
                    for t in log.read_bytes()[-500:].decode("utf-8", "replace").strip().splitlines()[-4:]:
                        print(f"        ! {t}")
    return 0


def cmd_stop(catalog: list[dict], targets: list[str], takeover: bool) -> int:
    picked = [e for e in catalog if not targets or e["id"] in targets]
    for e in reversed(picked):
        notes = stop_entry(e, takeover=takeover)
        print(f"[停止] {e['id']:<13} {'; '.join(notes) or '无托管进程'}")
    return 0


def cmd_watch(catalog: list[dict], targets: list[str], interval: float, once: bool = False) -> int:
    """看门狗：周期性探活，发现掉线的服务自动拉起（2026-10-15 新增）。

    背景：当日实测 P04 / P02-web 各静默死过一次（无 traceback、无自动恢复），
    演示中后端一挂整条链路就是 502。supervisor 此前是一次性 CLI、没有守护循环；
    这里只重启「端口未监听」的服务，不动已在线的进程。
    """
    picked = [e for e in catalog if not targets or e["id"] in targets]
    print(f"[watch] 每 {interval:.0f}s 探活 {len(picked)} 个服务（Ctrl+C 退出；--once 只跑一轮）")
    while True:
        for e in picked:
            if all(port_open(x) for x in e["ports"]):
                continue
            print(f"[{time.strftime('%H:%M:%S')}] [掉线] {e['id']:<13} 端口 {e['ports']} 未监听 → 拉起")
            spawn(e)
        if once:
            return 0
        time.sleep(interval)


def main() -> int:
    ap = argparse.ArgumentParser(description="李奕波个人作品矩阵全平台服务管理器")
    ap.add_argument("action", choices=["start", "stop", "restart", "status", "watch"])
    ap.add_argument("ids", nargs="*", help="服务 id，留空表示全部")
    ap.add_argument("--takeover", action="store_true",
                    help="接管端口上非本管理器启动的既有进程（先杀再起）")
    ap.add_argument("--verbose", action="store_true", help="status 时打印未启动服务的日志尾部")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--interval", type=float, default=15, help="watch 的探活间隔（秒）")
    ap.add_argument("--once", action="store_true", help="watch 只跑一轮就退出（自检用）")
    args = ap.parse_args()

    services = registry()
    catalog = build_catalog(services)
    ids = {e["id"] for e in catalog}
    for t in args.ids:
        if t not in ids:
            print(f"未知服务 id：{t}\n可选：{', '.join(sorted(ids))}")
            return 2

    if args.action == "status":
        return cmd_status(catalog, args.verbose)
    if args.action == "start":
        return cmd_start(catalog, args.ids, args.takeover)
    if args.action == "stop":
        return cmd_stop(catalog, args.ids, args.takeover)
    if args.action == "restart":
        cmd_stop(catalog, args.ids, takeover=True)
        time.sleep(1.5)
        return cmd_start(catalog, args.ids, takeover=False)
    if args.action == "watch":
        return cmd_watch(catalog, args.ids, args.interval, once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
