# -*- coding: utf-8 -*-
"""云枢智能 · 静默一键启动入口（给桌面应用程序 / pythonw 调用，不产生任何控制台窗口）。

    pythonw _tools/launcher.py            # 起全部服务（含 P01 的 MySQL 容器），门户就绪后自动开浏览器
    pythonw _tools/launcher.py stop       # 停全部服务
    python  _tools/launcher.py status     # 打印端口状态（给 exe 弹窗用）
    pythonw _tools/launcher.py start --no-mysql   # 不碰 Docker/MySQL（客服页会报加载失败）

与 start-all.bat 的区别：这里全程无窗口、无 pause，输出只落 _runtime/logs/launcher.log；
只有在服务没起来时才弹一个提示框，否则双击后用户看到的就是浏览器。
"""
from __future__ import annotations

import ctypes
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "_tools"))

LOG_DIR = ROOT / "_runtime" / "logs"
LOG_FILE = LOG_DIR / "launcher.log"
MB_ICONWARNING = 0x00000030
MB_YESNO = 0x00000004
MB_SETFRONT = 0x00080000
ERROR_ALREADY_EXISTS = 183
_GATE = None  # 持有命名互斥量的句柄，进程退出前不能丢


def acquire_gate(name: str = "CloudPivot_launcher") -> bool:
    """同一时刻只允许一个 start/stop 在跑（桌面图标连点、脚本重入都算）。"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, name)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    global _GATE
    _GATE = handle
    return True


def log(line: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "ab") as fh:
        fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {line}\n".encode("utf-8", "replace"))


def emit(line: str = "") -> None:
    """控制台可用就打印，不可用（pythonw）就只写日志。"""
    log(line)
    try:
        if sys.stdout is not None:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
        else:
            os.write(1, (line + "\n").encode("utf-8", "replace"))
    except Exception:
        pass


def notify(title: str, text: str) -> None:
    """静默模式下唯一的失败反馈；「是」打开日志目录。"""
    log(f"NOTIFY {title} :: {text.replace(chr(10), ' | ')}")
    try:
        ans = ctypes.windll.user32.MessageBoxW(0, text, title, MB_ICONWARNING | MB_YESNO | MB_SETFRONT)
        if ans == 6:
            os.startfile(str(LOG_DIR))  # noqa: S606
    except Exception:
        pass


def portal_url() -> str:
    import json

    data = json.loads((ROOT / "shared" / "config" / "services.json").read_text(encoding="utf-8"))
    port = int(data.get("gateway", {}).get("web_port", 8800))
    return f"http://127.0.0.1:{port}/"


def open_portal() -> None:
    url = portal_url()
    try:
        webbrowser.open(url)
    except Exception:
        os.startfile(url)
    emit(f"已打开门户 {url}")


# ------------------------------------------------------- P01 的 MySQL 容器依赖
COMPOSE = ROOT / "projects" / "p01-ai-customer-service" / "external" / "docker" / "docker-compose.yml"
DOCKER_APPS = (
    r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
    r"D:\Program Files\Docker\Docker\Docker Desktop.exe",
)


def listening(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def mysql_host_port() -> int:
    """宿主端口只在 compose 里定义一次，这里解析它，不另抄一份常量。"""
    try:
        text = COMPOSE.read_text(encoding="utf-8")
    except OSError:
        return 3307
    m = re.search(r"127\.0\.0\.1:(\d+):\d+", text) or re.search(r'^\s*"?(\d+):\d+"?\s*$', text, re.M)
    return int(m.group(1)) if m else 3307


def docker_engine_ready(engine_wait: float) -> tuple[bool, str]:
    """docker CLI 在不在、引擎通不通；引擎没跑就拉起 Docker Desktop 等它（只启动应用，不动它的任何配置）。"""
    docker = shutil.which("docker")
    if not docker:
        return False, "PATH 上没有 docker CLI"
    probe = [docker, "info", "-f", "{{.ServerVersion}}"]
    if subprocess.run(probe, capture_output=True, timeout=20).returncode == 0:
        return True, "引擎原本就在运行"
    app = next((p for p in DOCKER_APPS if Path(p).exists()), None)
    if not app:
        return False, "引擎没运行，且找不到 Docker Desktop.exe"
    subprocess.Popen([app])
    t0 = time.time()
    deadline = t0 + engine_wait
    while time.time() < deadline:
        try:
            if subprocess.run(probe, capture_output=True, timeout=20).returncode == 0:
                return True, f"引擎现场拉起，等了多少：{int(time.time() - t0)}s"
        except Exception:
            pass
        time.sleep(3.0)
    return False, f"拉起后等 {int(engine_wait)}s 引擎仍未就绪"


def ensure_mysql(engine_wait: float = 120.0, port_wait: float = 60.0) -> tuple[bool, str]:
    """P01 客服后端与商城中台都连这个 MySQL。

    它不在 SERVICE_REGISTRY 里（那是业务模块的注册表），桌面图标要是不管它，
    客服页就会稳定报「加载历史消息失败 / 加载订单列表失败」——
    两个接口 500，日志里是 `Can't connect to MySQL server on '127.0.0.1'`。
    """
    port = mysql_host_port()
    if listening(port):
        return True, f"MySQL :{port} 已在监听"
    if not COMPOSE.exists():
        return False, f"找不到 compose：{COMPOSE}"
    ok, why = docker_engine_ready(engine_wait)
    if not ok:
        return False, f"MySQL 未启动（{why}）"
    docker = shutil.which("docker")
    res = subprocess.run([docker, "compose", "-f", str(COMPOSE), "up", "-d"],
                         capture_output=True, timeout=300)
    if res.returncode != 0:
        tail = (res.stderr or res.stdout or b"").decode("utf-8", "replace").strip()[-200:]
        return False, f"compose up 失败：{tail}"
    deadline = time.time() + port_wait
    while time.time() < deadline:
        if listening(port):
            return True, f"MySQL :{port} 已就绪（容器随启动器拉起）"
        time.sleep(1.0)
    return False, f"容器已 up，但 :{port} 在 {int(port_wait)}s 内没监听（首次建库可能更久，看 docker logs）"


def do_start(wait_seconds: float, with_mysql: bool = True) -> int:
    import supervisor as sup

    # 先管 P01 的 MySQL：它不归 SERVICE_REGISTRY 管，也不在这 15 个进程里，
    # 但少了它「AI 电商客服」整页就是两个加载失败。
    mysql_note = ""
    if with_mysql:
        ok, why = ensure_mysql()
        emit(f"[MySQL] {why}")
        if not ok:
            mysql_note = why

    catalog = sup.build_catalog(sup.registry())
    up = [e for e in catalog if all(sup.port_open(p) for p in e["ports"])]
    pending = [e for e in catalog if e not in up]
    emit(f"start: {len(up)} 已在线，{len(pending)} 待启动")
    for e in pending:
        cwd = ROOT / e["cwd"]
        if not cwd.is_dir():
            emit(f"[失败] {e['id']} 目录不存在 {cwd}")
            continue
        try:
            sup.spawn(e)
            emit(f"[启动] {e['id']:<13} {sup.render_cmd(e)}")
        except Exception as exc:
            emit(f"[失败] {e['id']} {exc}")

    # 门户一起来就开浏览器，其余服务在后台继续就绪，避免用户干等。
    gateway = next((e for e in catalog if e["id"] == "shell"), None)
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if gateway and all(sup.port_open(p) for p in gateway["ports"]):
            break
        time.sleep(0.5)
    if not (gateway and all(sup.port_open(p) for p in gateway["ports"])):
        notify("云枢智能：外壳网关没起来",
               f"门户 {portal_url()} 未能访问。\n日志：{LOG_FILE}\n\n打开日志目录？")
        return 1
    open_portal()

    # 初值按「全部待启动都没就绪」算：万一等待窗口已被门户耗尽，也不能报成「全在线」。
    still_down: list[str] = [e["id"] for e in pending]
    while time.time() < deadline:
        still_down = [e["id"] for e in pending
                      if not all(sup.port_open(p) for p in e["ports"])]
        if not still_down:
            break
        time.sleep(1.0)
    if still_down:
        emit("未就绪：" + ", ".join(still_down))
    problems: list[str] = []
    if still_down:
        problems.append("这些端口没起来：\n" + "\n".join(still_down))
    if mysql_note:
        problems.append("P01 客服依赖的 MySQL 没就绪，客服页会报"
                        "「加载历史消息失败 / 加载订单列表失败」：\n" + mysql_note)
    if problems:
        notify("云枢智能：有依赖没就绪",
               "\n\n".join(problems) + f"\n\n日志目录：{LOG_FILE}\n\n打开日志目录？")
        return 0
    emit(f"全部 {len(catalog)} 个服务在线")
    return 0


def do_stop() -> int:
    import supervisor as sup

    catalog = sup.build_catalog(sup.registry())
    sup.cmd_stop(catalog, [], True)
    emit("已发送停止指令")
    time.sleep(2.0)
    down = [e["id"] for e in catalog if any(sup.port_open(p) for p in e["ports"])]
    emit("仍在监听：" + ", ".join(down) if down else "全部端口已释放")
    return 0


def do_status() -> int:
    import supervisor as sup

    return sup.cmd_status(sup.build_catalog(sup.registry()))


def main() -> int:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    action = pos[0] if pos else "start"
    wait_seconds = float(pos[1]) if len(pos) > 1 else 120.0
    if action == "stop":
        if not acquire_gate():
            emit("已有启动器在跑，本次 stop 跳过")
            return 0
        return do_stop()
    if action == "status":
        return do_status()
    if action == "open":
        open_portal()
        return 0
    if action == "start":
        if not acquire_gate():
            emit("已有启动器在跑，本次 start 跳过")
            return 0
        return do_start(wait_seconds, with_mysql="--no-mysql" not in flags)
    emit(f"未知动作 {action}")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # pythonw 下没有控制台，异常必须落日志并弹窗，否则用户只看到「双击没反应」
        err = traceback.format_exc()
        log("FATAL\n" + err)
        notify("云枢智能：启动器出错", err[-800:] + f"\n\n完整日志：{LOG_FILE}")
        sys.exit(1)
