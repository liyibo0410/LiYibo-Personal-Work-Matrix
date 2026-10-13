# -*- coding: utf-8 -*-
"""比对 SERVICE_REGISTRY 声明的端口与 netstat 实际监听地址。"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(r"D:\software\PycharmProjects\面试项目")
reg = json.loads((ROOT / "shared" / "config" / "services.json").read_text(encoding="utf-8"))

out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
listen = {}
for line in out.splitlines():
    m = re.search(r"TCP\s+(\S+)\s+0\.0\.0\.0:0\s+LISTENING\s+(\d+)", line)
    if m:
        addr, pid = m.group(1), int(m.group(2))
        port = int(addr.rsplit(":", 1)[1])
        listen.setdefault(port, []).append((addr, pid))

rows = []
for sid, s in reg["services"].items():
    for key in ("api_port", "web_port", "commerce_port"):
        p = s.get(key)
        if not p:
            continue
        hits = listen.get(p, [])
        addrs = sorted({a.rsplit(":", 1)[0] for a, _ in hits})
        bind = "UP-ALL" if any(a == "0.0.0.0" for a in addrs) else ("UP-LOOP" if addrs else "DOWN")
        rows.append((sid, key, p, bind, ",".join(addrs) or "-"))

w = max(len(r[4]) for r in rows)
print(f"{'svc':<5} {'field':<15} {'port':>6}  {'state':<8} bind")
for sid, key, p, bind, addrs in rows:
    print(f"{sid:<5} {key:<15} {p:>6}  {bind:<8} {addrs}")

print("\n--- summary ---")
for st in ("UP-ALL", "UP-LOOP", "DOWN"):
    n = sum(1 for r in rows if r[3] == st)
    print(f"{st}: {n}")
print("\nUP-LOOP detail:", [f"{r[0]}.{r[1]}:{r[2]}" for r in rows if r[3] == "UP-LOOP"])
print("DOWN detail:", [f"{r[0]}.{r[1]}:{r[2]}" for r in rows if r[3] == "DOWN"])
