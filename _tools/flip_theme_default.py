"""把全平台的主题默认从「深色」翻到「白底」，并把主题存储键统一升到 cp_theme_v2。

为什么升键：旧浏览器里存的 "dark" 是「深色曾是平台默认」时由 CP.initTheme() 自动写入的，
不是用户主动选的。沿用旧键会让白底默认永远翻不回来。所有读写方必须一起升键，
否则外壳切了主题、模块不跟随。

只动主题默认值与存储键，不动颜色值（颜色在 shared/ui-kit/tokens.css 里）。
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKUP = ROOT / "_runtime" / "whiteblue-backup" / "theme-defaults"

OLD_KEY = "cp_theme"
NEW_KEY = "cp_theme_v2"

# 每个文件：[(旧片段, 新片段, 期望命中次数)]
PLAN: dict[str, list[tuple[str, str, int]]] = {
    "projects/p01-ai-customer-service/external/customer-service-frontend/index.html": [
        ('<html lang="zh-CN" data-theme="dark">', '<html lang="zh-CN" data-theme="light">', 1),
    ],
    "projects/p01-ai-customer-service/external/customer-service-frontend/src/main.js": [
        ("const THEME_KEY = 'cp_theme'", f"const THEME_KEY = '{NEW_KEY}'", 1),
        ("let stored = 'dark'", "let stored = 'light'", 1),
        ("localStorage.getItem(THEME_KEY) || 'dark'", "localStorage.getItem(THEME_KEY) || 'light'", 1),
        ("t === 'light' ? 'light' : 'dark'", "t === 'dark' ? 'dark' : 'light'", 2),
    ],
    "projects/p02-ecommerce-ops-assistant/web/src/lib/theme.ts": [
        ('export const THEME_KEY = "cp_theme";', f'export const THEME_KEY = "{NEW_KEY}";', 1),
    ],
    "projects/p02-ecommerce-ops-assistant/web/src/components/cp-theme-bridge.tsx": [
        ('const value = normalizeTheme(theme) ?? "dark";', 'const value = normalizeTheme(theme) ?? "light";', 1),
        ('applyTheme(themeFromUrl() || readPersistedTheme() || "dark");',
         'applyTheme(themeFromUrl() || readPersistedTheme() || "light");', 1),
        ('if (data.type === "cp:theme") applyTheme(data.theme || "dark");',
         'if (data.type === "cp:theme") applyTheme(data.theme || "light");', 1),
    ],
    "projects/p02-ecommerce-ops-assistant/web/src/app/layout.tsx": [
        ('const theme = (await cookies()).get(THEME_KEY)?.value === "light" ? "light" : "dark";',
         'const theme = (await cookies()).get(THEME_KEY)?.value === "dark" ? "dark" : "light";', 1),
    ],
    "projects/p03-deep-research/ui/index.html": [
        ('<html lang="zh-CN" data-theme="dark">', '<html lang="zh-CN" data-theme="light">', 1),
    ],
    "projects/p03-deep-research/ui/src/main.ts": [
        ("const THEME_KEY = 'cp_theme'", f"const THEME_KEY = '{NEW_KEY}'", 1),
        ("t === 'light' ? 'light' : 'dark'", "t === 'dark' ? 'dark' : 'light'", 2),
        ("localStorage.getItem(THEME_KEY) || 'dark' } catch (e) { return 'dark' }",
         "localStorage.getItem(THEME_KEY) || 'light' } catch (e) { return 'light' }", 1),
    ],
    "projects/p05-contract-review/ui/assets/app.js": [
        ("localStorage.getItem('cp_theme')", f"localStorage.getItem('{NEW_KEY}')", 1),
        ("localStorage.setItem('cp_theme', cur)", f"localStorage.setItem('{NEW_KEY}', cur)", 1),
        ("if (saved !== 'light' && saved !== 'dark') saved = 'dark';",
         "if (saved !== 'light' && saved !== 'dark') saved = 'light';", 1),
    ],
}

# P05 的 7 个页面各自内联了一段主题引导脚本，模式完全相同
for page in ("index", "login", "denied", "mock", "rules", "twin", "workbench"):
    PLAN[f"projects/p05-contract-review/ui/{page}.html"] = [
        ('<html lang="zh-CN" data-theme="dark">', '<html lang="zh-CN" data-theme="light">', 1),
        ("localStorage.getItem('cp_theme')", f"localStorage.getItem('{NEW_KEY}')", 1),
        ("if (t !== 'light' && t !== 'dark') t = 'dark';",
         "if (t !== 'light' && t !== 'dark') t = 'light';", 1),
    ]


def main() -> int:
    problems: list[str] = []
    changed = 0
    for rel, edits in sorted(PLAN.items()):
        path = ROOT / rel
        if not path.exists():
            problems.append(f"缺文件：{rel}")
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new, want in edits:
            got = text.count(old)
            if got != want:
                problems.append(f"{rel}：「{old[:48]}」命中 {got} 次，期望 {want} 次 —— 该处未改")
                continue
            text = text.replace(old, new)
        if text != original:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(path, dst)
            path.write_text(text, encoding="utf-8", newline="")
            changed += 1
    sys.stdout.write(f"改过 {changed} 个文件\n")
    if problems:
        sys.stdout.write("需要人工确认：\n")
        for p in problems:
            sys.stdout.write("  - " + p + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
