# -*- coding: utf-8 -*-
"""服务器 nginx cloudpivot-demo.conf 加固（在服务器上运行）：
1) 同址双 peer upstream（19000-19100 各一组）+ proxy_next_upstream —— 隧道瞬断的
   首个失败请求自动重放，访客不再看到偶发 502；
2) map $http_upgrade -> Connection：普通请求走 keepalive（Connection 空），WS 请求仍升级；
3) proxy_connect_timeout 3s：真断时快速失败，不让访客干等；
4) Host 头保持字面量不动 —— proxy_redirect 的 30x 前缀保留正则依赖 127.0.0.1:190XX，
   换 $host（无端口）会弄坏它，且全部后端都不依赖 Host。
先备份再改；改完 nginx -t，失败自动回滚。
"""
import re
import shutil
import subprocess
import sys
import time

CONF = "/etc/nginx/conf.d/cloudpivot-demo.conf"
STAMP = time.strftime("%Y%m%d%H%M%S")
BAK = CONF + ".bak-hostfix-" + STAMP

src = open(CONF, encoding="utf-8").read()

# ---- 0) 备份 ----
shutil.copyfile(CONF, BAK)
print("backup ->", BAK)

if "cp_u_19000" in src:
    print("already patched, nothing to do")
    sys.exit(0)

# ---- 1) 追加 map + upstream 组（插在第一个 server { 之前）----
helpers = [
    "",
    "# ---- 2026-10-15 hostfix：WS/keepalive 兼容 + 同址双 peer 自动重试（防隧道瞬断 502）----",
    "map $http_upgrade $cp_conn {",
    "    default upgrade;",
    "    ''      \"\";",
    "}",
    "",
]
for p in range(19000, 19011):
    helpers += [
        "upstream cp_u_%d {" % p,
        "    server 127.0.0.1:%d;" % p,
        "    server 127.0.0.1:%d;" % p,  # 同址双 peer：给 proxy_next_upstream 一个可重试的“下一跳”
        "    keepalive 8;",
        "}",
        "",
    ]
helpers.append("server {")  # 把原来被吃掉的第一个 server 开头补回来

idx = src.index("\nserver {")
src = src[:idx] + "\n" + "\n".join(helpers[:-1]) + "\n" + src[idx + 1:]

# ---- 2) proxy_pass 指到 upstream 组（$cp_route 的兜底 location 不动）----
n_pass = 0
def sub_pass(m):
    global n_pass
    n_pass += 1
    return "proxy_pass http://cp_u_%s;" % m.group(1)
src = re.sub(r"proxy_pass http://127\.0\.0\.1:(190\d\d);", sub_pass, src)

# ---- 3) Connection 走 $cp_conn ----
n_conn = src.count('proxy_set_header Connection "upgrade";')
src = src.replace('proxy_set_header Connection "upgrade";',
                  "proxy_set_header Connection $cp_conn;")

# ---- 4) server 级重试与快速失败（插在两个 server_name _; 之后）----
retry = [
    "    proxy_next_upstream error timeout http_502 http_503 http_504;",
    "    proxy_next_upstream_tries 2;",
    "    proxy_next_upstream_timeout 6s;",
    "    proxy_connect_timeout 3s;",
]
n_srv = src.count("    server_name _;")
src = src.replace("    server_name _;",
                  "    server_name _;\n" + "\n".join(retry))

print("proxy_pass rewritten:", n_pass, "| Connection:", n_conn, "| server blocks:", n_srv)
if n_pass != 11 or n_conn < 12 or n_srv != 2:
    print("UNEXPECTED counts, aborting (backup untouched at", BAK + ")")
    sys.exit(1)

open(CONF, "w", encoding="utf-8").write(src)
print("written", CONF)

# ---- 5) nginx -t，失败回滚 ----
t = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
print(t.stderr.strip())
if t.returncode != 0:
    shutil.copyfile(BAK, CONF)
    print("nginx -t FAILED -> rolled back to", BAK)
    sys.exit(2)

r = subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True)
print("reload:", (r.stdout + r.stderr).strip() or "ok", "rc=", r.returncode)
sys.exit(0 if r.returncode == 0 else 3)
