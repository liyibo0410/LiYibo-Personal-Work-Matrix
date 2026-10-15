# -*- coding: utf-8 -*-
"""李奕波个人作品矩阵统一平台 · 对外演示隧道（cloudflared Quick Tunnel）

给「外壳网关 + 各模块前端端口」各开一条临时公网 https 隧道，把随机域名写成
`_runtime/tunnel/public_urls.json`。网关的 `/api/services/health` 会把它随探活一起下发，
前端据此挂 iframe —— 所以域名每次重启都变，也不需要重新生成 `services.js`。

    python _tools/tunnel.py start              # 开隧道并打印可分享的链接
    python _tools/tunnel.py start --only shell,p06,p04
    python _tools/tunnel.py status             # 看当前链接与存活
    python _tools/tunnel.py stop               # 收工：关掉全部隧道

前置：先 `python _tools/supervisor.py start` 把服务拉起来；cloudflared 二进制路径取
环境变量 `CP_CLOUDFLARED`，默认 `E:\\qoder-tools\\cloudflared\\cloudflared.exe`。

诚实边界：Quick Tunnel 的域名是随机的、进程一停就失效，且本机 15 个服务会直接暴露公网
（演示账号是弱口令）。演示结束务必 `stop`。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "_runtime" / "tunnel"
PID_DIR = RUNTIME / "pids"
OUT_FILE = RUNTIME / "public_urls.json"
DEFAULT_BIN = Path(r"E:\qoder-tools\cloudflared\cloudflared.exe")
# 只认分配到的随机域名；日志里还会先出现 api.trycloudflare.com / www.trycloudflare.com 这类提示链接。
HOSTNAME_RE = re.compile(r"https://(?!api\.|www\.)[a-z0-9][a-z0-9-]*\.trycloudflare\.com")
# 隧道建立要等 Cloudflare 边缘分配域名，实测 5~20s；再长就当失败。
WAIT_SECONDS = 60


def registry() -> dict:
    with open(REPO / "shared" / "config" / "services.json", encoding="utf-8") as f:
        return json.load(f)


def tunnel_targets(reg: dict, only: list[str] | None) -> list[tuple[str, int]]:
    """[(标识, 本地端口)]：shell 用网关端口，模块用 web_port（web==api 的模块只开一条）。"""
    out: list[tuple[str, int]] = [("shell", int(os.environ.get("CP_SHELL_PORT", "8800")))]
    for sid, svc in sorted(reg.get("services", {}).items()):
        port = svc.get("web_port") or svc.get("api_port")
        if port and (sid, int(port)) not in out:
            out.append((sid, int(port)))
    if only:
        wanted = set(only)
        out = [t for t in out if t[0] in wanted]
    # 同一端口只开一条：P04/P05 这类 web==api 的模块，以及端口重复的条目。
    seen: set[int] = set()
    return [(k, p) for k, p in out if not (p in seen or seen.add(p))]


def alive(pids: dict) -> dict:
    still = {}
    for key, pid in pids.items():
        try:
            os.kill(int(pid), 0)
            still[key] = int(pid)
        except (OSError, ValueError):
            pass
    return still


def read_pid_file() -> dict:
    if not PID_DIR.exists():
        return {}
    out = {}
    for f in PID_DIR.glob("*.pid"):
        try:
            out[f.stem] = int(f.read_text().strip())
        except ValueError:
            pass
    return out


def cmd_stop() -> int:
    pids = read_pid_file()
    if not pids:
        print("没有正在运行的隧道。")
        return 0
    for key, pid in pids.items():
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                os.kill(pid, signal.SIGTERM)
            print(f"[停止] {key:<13} pid={pid}")
        except OSError as exc:
            print(f"[失败] {key:<13} pid={pid} {exc}")
        (PID_DIR / f"{key}.pid").unlink(missing_ok=True)
    OUT_FILE.unlink(missing_ok=True)
    print("隧道已全部关闭，公网链接即刻失效。")
    return 0


def probe_url(url: str, timeout: float = 8.0) -> tuple[bool, str]:
    """自校验：真的能取到网关 /api/health 才算这条隧道可用。

    只看 cloudflared 打印的域名会骗人 —— 边缘 TLS 握手失败时域名照样分配，
    访客拿到的却是 530。本机 TLS 被 VPN 中间人过，故不校验证书链。
    """
    import ssl
    import urllib.error
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/health", timeout=timeout, context=ctx) as r:
            body = r.read(200).decode("utf-8", "ignore")
            return (r.status == 200 and '"ok"' in body), "HTTP %s" % r.status
    except urllib.error.HTTPError as exc:
        return False, "HTTP %s" % exc.code
    except Exception as exc:      # noqa: BLE001 —— 任何异常都归为「不可用」，把原因回显给人
        return False, type(exc).__name__ + ": " + str(exc)[:120]


def cmd_start(only: list[str] | None, protocol: str) -> int:
    exe = Path(os.environ.get("CP_CLOUDFLARED", str(DEFAULT_BIN)))
    if not exe.is_file():
        print(f"[缺二进制] 找不到 cloudflared：{exe}\n"
              f"  下载：curl -L -o {exe} https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe")
        return 2
    RUNTIME.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)

    targets = tunnel_targets(registry(), only)
    host = "127.0.0.1"
    procs: dict[str, subprocess.Popen] = {}
    logs: dict[str, Path] = {}
    for key, port in targets:
        log = RUNTIME / f"{key}.log"
        log.write_text("", encoding="utf-8")
        logs[key] = log
        args = [str(exe), "tunnel", "--no-autoupdate",
                "--url", f"http://{host}:{port}", "--protocol", protocol]
        if os.name == "nt":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            fh = open(log, "ab")
            procs[key] = subprocess.Popen(args, creationflags=flags,
                                          stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        else:
            procs[key] = subprocess.Popen(args, stdout=open(log, "ab"),
                                          stderr=subprocess.STDOUT, start_new_session=True)
        (PID_DIR / f"{key}.pid").write_text(str(procs[key].pid), encoding="utf-8")
        print(f"[启动] {key:<13} -> {host}:{port}")

    print(f"\n等待 Cloudflare 分配域名（最多 {WAIT_SECONDS}s）…")
    urls: dict[str, str] = {}
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline and len(urls) < len(targets):
        for key, _port in targets:
            if key in urls:
                continue
            text = logs[key].read_text(encoding="utf-8", errors="ignore")
            hit = HOSTNAME_RE.search(text)
            if hit:
                urls[key] = hit.group(0)
                print(f"  [就绪] {key:<13} {urls[key]}")
            elif "error" in text.lower() and "TLS handshake" in text:
                print(f"  [受阻] {key:<13} 与 Cloudflare 边缘的 TLS 握手被拦截，详见 {logs[key]}")
                urls[key] = ""
        if len(urls) < len(targets):
            time.sleep(1.5)

    shell_url = urls.pop("shell", "")
    missing = [k for k, _ in targets if k != "shell" and k not in urls]

    print("\n" + "=" * 66)
    if not shell_url:
        print("隧道没建起来 —— 连外壳自己的公网域名都没分配到。")
        print(f"看日志： {RUNTIME / 'shell.log'}")
        return 1

    # 域名分配 ≠ 可用：边缘 TLS 被拦时访客只会拿到 530，所以先自校验再对外发链接。
    ok, why = False, "未探测"
    for _ in range(6):
        ok, why = probe_url(shell_url)
        if ok:
            break
        time.sleep(4)
    if not ok:
        print(f"链接不可用： {shell_url}  →  {why}")
        print("域名已分配但取不到内容，通常是本机到 Cloudflare 边缘的连接没建立。")
        print("本机若在 VPN/代理的 TUN 模式下，argotunnel.com 的 TLS 会被中间人掐断；")
        print("给 argotunnel.com / trycloudflare.com 加 DIRECT 且跳过 TLS 中间人，或演示时暂停 TUN。")
        print(f"日志： {RUNTIME / 'shell.log'}")
        print("=" * 66)
        return 1

    payload = {"generated_at": int(time.time()), "protocol": protocol,
               "shell": shell_url, "urls": {k: v for k, v in urls.items() if v}}
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"可分享的链接： {shell_url}   （已实测 /api/health 200）")
    print("演示账号： owner / owner123（或 ops、legal、sales，口令同为 <用户名>123）")
    print(f"已下发模块地址： {len(payload['urls'])}/{len(targets) - 1}"
          + (f"（缺 {', '.join(missing)}）" if missing else ""))
    print("收工执行： python _tools\\tunnel.py stop   —— 不停掉就一直暴露公网")
    print("=" * 66)
    return 0


def cmd_status() -> int:
    pids = alive(read_pid_file())
    if not pids:
        print("当前没有隧道进程在跑。")
        return 0
    data = json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else {}
    print(f"{'标识':<14}{'PID':<10}公网地址")
    for key in sorted(pids):
        url = data.get("shell") if key == "shell" else (data.get("urls") or {}).get(key, "")
        print(f"{key:<14}{pids[key]:<10}{url or '(未就绪)'}")
    print(f"\n生成时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data.get('generated_at', 0)))}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="李奕波个人作品矩阵对外演示隧道")
    ap.add_argument("action", choices=["start", "stop", "status"])
    ap.add_argument("--only", default="", help="逗号分隔的标识白名单，如 shell,p06,p04")
    ap.add_argument("--protocol", default=os.environ.get("CP_TUNNEL_PROTOCOL", "http2"),
                    choices=["http2", "quic"], help="边缘连接协议；本机网络拦 QUIC 时用 http2")
    args = ap.parse_args()
    only = [s.strip() for s in args.only.split(",") if s.strip()] or None
    if args.action == "stop":
        return cmd_stop()
    if args.action == "status":
        return cmd_status()
    return cmd_start(only, args.protocol)


if __name__ == "__main__":
    sys.exit(main())
