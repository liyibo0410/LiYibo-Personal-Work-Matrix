import json
import ssl
import time
import urllib.error
import urllib.request

ROOT = r"D:\software\PycharmProjects\面试项目"
CTX = ssl.create_default_context()


def load_env(path):
    d = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def req(url, key, payload=None, tries=4):
    last = None
    for i in range(tries):
        data = json.dumps(payload).encode() if payload is not None else None
        r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        r.add_header("Authorization", "Bearer " + key)
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=45, context=CTX) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            last = repr(e)
            time.sleep(2 + 2 * i)
    return None, "CONNECT_FAIL: " + last


def main():
    env = load_env(ROOT + r"\.env")
    endpoints = [
        ("FREE(sk-ws-)", env["CODING_BASE_URL_ALT"], env["CODING_API_KEY"]),
        ("ESSENTIAL(sk-sp-)", env["LLM_BASE_URL_FALLBACK"], env["LLM_API_KEY_FALLBACK"]),
    ]
    out = []
    for name, base, key in endpoints:
        out.append("=== %s  %s" % (name, base))
        code, body = req(base + "/models", key)
        ids = []
        if code == 200:
            ids = sorted(m["id"] for m in json.loads(body)["data"])
            out.append("  /models -> 200 (%d): %s" % (len(ids), ", ".join(ids)))
        else:
            out.append("  /models -> %s %s" % (code, body[:220]))
        cand = [m for m in ("qwen3.8-max", "qwen3.8-flash", "qwen3.7-plus") if m in ids] or ids[:2]
        for model in cand:
            code, body = req(
                base + "/chat/completions",
                key,
                {"model": model, "messages": [{"role": "user", "content": "只回复两个字：通了"}],
                 "max_tokens": 20, "temperature": 0},
            )
            if code == 200:
                j = json.loads(body)
                txt = j["choices"][0]["message"]["content"]
                out.append("  chat %-16s -> 200 ok=%s usage=%s reply=%r"
                           % (model, j.get("id", "")[:6], j.get("usage"), txt[:40]))
            else:
                out.append("  chat %-16s -> %s %s" % (model, code, body[:220]))
    text = "\n".join(out)
    with open(ROOT + r"\_tmp_issue\probe_llm.txt", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)


main()
