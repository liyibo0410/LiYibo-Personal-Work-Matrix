# -*- coding: utf-8 -*-
"""生成「云枢智能」桌面应用程序并安装到桌面。

产物：
  _tools/assets/cloudpivot.ico      —— 从 shared/config/brand.json 的 logo 生成（多尺寸）
  _tools/dist/云枢智能.exe            —— csc.exe 编译的无控制台启动器（不依赖额外运行时）
  桌面\云枢智能 一键启动.lnk           —— 静默起全部服务并自动打开门户
  桌面\云枢智能 停止服务.lnk           —— 静默停全部服务
  桌面\云枢智能 服务状态.lnk           —— 弹窗显示 15 个端口探活结果

改端口/改品牌/移动仓库后重跑本脚本即可（exe 里烘焙了仓库绝对路径，并有「相对自身位置」兜底）。

用法：
    python -X utf8 _tools/make_desktop_app.py            # 图标 + exe + 桌面快捷方式
    python -X utf8 _tools/make_desktop_app.py --no-lnk   # 只重建图标和 exe
"""
from __future__ import annotations

import argparse
import base64
import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "_tools" / "assets"
DIST = ROOT / "_tools" / "dist"
BRAND = ROOT / "shared" / "config" / "brand.json"
LAUNCHER = ROOT / "_tools" / "launcher.py"
ICO = ASSETS / "cloudpivot.ico"
EXE = DIST / "云枢智能.exe"
CS = DIST / "cloudpivot_launcher.cs"
CSC = Path(r"C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe")
IS_WIN = os.name == "nt"


def desktop_dir() -> Path:
    buf = ctypes.create_unicode_buffer(260)
    if IS_WIN and ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf) == 0:
        return Path(buf.value)
    return Path.home() / "Desktop"


def pythonw_path() -> str:
    """优先当前解释器同目录的 pythonw，再按惯例扫一遍用户目录。"""
    cand = Path(sys.executable).with_name("pythonw.exe")
    if cand.exists():
        return str(cand)
    local = Path.home() / "AppData" / "Local" / "Programs" / "Python"
    if local.is_dir():
        for ver in sorted(local.iterdir(), reverse=True):
            pw = ver / "pythonw.exe"
            if pw.exists():
                return str(pw)
    found = subprocess.run(["where", "pythonw"], capture_output=True, text=True)
    first = (found.stdout or "").splitlines()
    return first[0].strip() if first else ""


def build_icon() -> bool:
    """品牌 logo（data URL PNG）→ 多尺寸 .ico。logo 换了就重跑本脚本。"""
    try:
        from PIL import Image
    except ImportError:
        print("[警告] 当前解释器没有 Pillow，跳过图标（快捷方式将用 exe 默认图标）")
        return False

    logo = json.loads(BRAND.read_text(encoding="utf-8")).get("logo", "")
    b64 = logo.split(",", 1)[1] if logo.startswith("data:") else logo
    if not b64:
        print("[警告] brand.json 里没有 logo，跳过图标")
        return False

    ASSETS.mkdir(parents=True, exist_ok=True)
    import io

    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    img.save(ICO, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print(f"[图标] {ICO}  <- {BRAND.name} logo {img.size[0]}x{img.size[1]}")
    return True


CS_TEMPLATE = r'''
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

// 云枢智能桌面启动器：无控制台窗口，把活儿交给 _tools\launcher.py（pythonw 静默跑）。
// 由 _tools\make_desktop_app.py 生成并编译，不要手改。
class CloudPivotLauncher
{
    const string BakedRoot = @"@@ROOT@@";
    const string BakedPythonw = @"@@PYTHONW@@";

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();

    const uint MB_OK = 0x0;
    const uint MB_ICONWARNING = 0x30;
    const uint MB_SETFRONT = 0x80000;

    static int Alert(string text, string caption)
    {
        return MessageBoxW(GetForegroundWindow(), text, caption, MB_OK | MB_ICONWARNING | MB_SETFRONT);
    }

    static string RepoRoot()
    {
        // 烘焙路径优先；仓库被移动时，从 exe 自身位置往回找（exe 在 _tools\dist\）。
        if (Directory.Exists(BakedRoot) &&
            File.Exists(Path.Combine(BakedRoot, "_tools", "launcher.py")))
            return BakedRoot;

        try
        {
            string dir = Path.GetDirectoryName(
                System.Reflection.Assembly.GetExecutingAssembly().Location);
            for (int i = 0; i < 5 && dir != null; i++)
            {
                string cand = Path.GetFullPath(Path.Combine(dir, "_tools", "launcher.py"));
                if (File.Exists(cand)) return Path.GetDirectoryName(Path.GetDirectoryName(cand));
                dir = Path.GetDirectoryName(dir);
            }
        }
        catch { }
        return null;
    }

    static string Pythonw()
    {
        if (File.Exists(BakedPythonw)) return BakedPythonw;
        foreach (string p in new string[] {
            Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"),
            Environment.ExpandEnvironmentVariables(@"%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"),
            Environment.ExpandEnvironmentVariables(@"%ProgramFiles%\Python312\pythonw.exe") })
        {
            if (File.Exists(p)) return p;
        }
        return null;
    }

    static Process Start(string root, string py, string args, bool capture)
    {
        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = py;
        // -X utf8：管道里的中文按 UTF-8 输出，与上面的 StandardOutputEncoding 对齐
        psi.Arguments = "-X utf8 \"" + Path.Combine(root, "_tools", "launcher.py") + "\" " + args;
        psi.WorkingDirectory = root;
        psi.UseShellExecute = false;      // 必须：CreateNoWindow 只在非 ShellExecute 下生效
        psi.CreateNoWindow = true;
        psi.WindowStyle = ProcessWindowStyle.Hidden;
        if (capture)
        {
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.StandardOutputEncoding = Encoding.UTF8;
        }
        return Process.Start(psi);
    }

    [STAThread]
    static void Main(string[] argv)
    {
        string mode = argv.Length > 0 ? argv[0].TrimStart('-').ToLower() : "start";
        string root = RepoRoot();
        string py = Pythonw();

        if (root == null)
        {
            Alert("找不到云枢智能工程目录。\n\n期望位置：" + BakedRoot +
                  "\n\n仓库搬家了的话，在新位置运行：\npython -X utf8 _tools\\make_desktop_app.py",
                  "云枢智能");
            return;
        }
        bool hasPy = !string.IsNullOrEmpty(py) && File.Exists(py);
        if (!hasPy && mode != "status")
        {
            Alert("找不到 pythonw.exe（期望 " + BakedPythonw +
                  "）。装好 Python 3.11+ 后重跑：\npython -X utf8 _tools\\make_desktop_app.py",
                  "云枢智能");
            return;
        }

        if (mode == "status")
        {
            // 状态要读管道，用同目录的 python.exe；CreateNoWindow 保证仍然看不见黑窗。
            string console = "python.exe";
            if (hasPy)
            {
                string cand = Path.Combine(Path.GetDirectoryName(py), "python.exe");
                if (File.Exists(cand)) console = cand;
            }
            try
            {
                Process p = Start(root, console, "status 150", true);
                string text = p.StandardOutput.ReadToEnd();
                p.WaitForExit(30000);
                Alert(text.Length > 0 ? text : "没有输出，检查 _tools\\launcher.py", "云枢智能 · 服务状态");
            }
            catch (Exception e)
            {
                Alert("读取状态失败：" + e.Message, "云枢智能");
            }
            return;
        }

        // 同一个动作别重复双击：抢不到互斥锁就直接退出，后台那次已在跑。
        bool created;
        Mutex gate = new Mutex(true, "CloudPivot_Launcher_" + mode, out created);
        if (!created) return;

        try
        {
            // start / stop 都是「发射后不管」：launcher.py 自己等就绪、开浏览器、
            // 失败才弹窗，所以这里不 WaitForExit，桌面图标不能卡住。
            Start(root, py, mode, false);
        }
        catch (Exception e)
        {
            Alert("启动器没能跑起来：" + e.Message, "云枢智能");
        }
        finally
        {
            gate.ReleaseMutex();
        }
    }
}
'''


def build_exe() -> None:
    if not IS_WIN or not CSC.exists():
        print(f"[失败] 找不到编译器 {CSC}")
        sys.exit(1)

    DIST.mkdir(parents=True, exist_ok=True)
    cs = (CS_TEMPLATE.replace("@@ROOT@@", str(ROOT))
                    .replace("@@PYTHONW@@", pythonw_path()))
    # UTF-8 BOM：csc 按 ANSI 读中文文件名/字面量会乱码
    CS.write_bytes(b"\xef\xbb\xbf" + cs.encode("utf-8"))

    args = [str(CSC), "/nologo", "/target:winexe", "/optimize+", "/platform:anycpu",
            f"/out:{EXE}"]
    if ICO.exists():
        args.append(f"/win32icon:{ICO}")
    args.append(str(CS))
    res = subprocess.run(args, capture_output=True, cwd=str(ROOT))
    out = (res.stdout or b"").decode("gbk", "replace") + (res.stderr or b"").decode("gbk", "replace")
    if res.returncode != 0:
        print(out)
        print(f"[失败] 编译 {EXE.name} 返回码 {res.returncode}")
        sys.exit(1)
    print(f"[程序] {EXE}  {EXE.stat().st_size} bytes")


def psq(text: str) -> str:
    """PowerShell 单引号字面量（内部单引号翻倍）。"""
    return "'" + text.replace("'", "''") + "'"


def build_shortcuts(desktop: Path) -> None:
    items = [
        ("云枢智能 一键启动.lnk", "", "静默启动全部服务并打开门户 http://127.0.0.1:8800"),
        ("云枢智能 停止服务.lnk", "--stop", "静默停止全部服务（含占用端口的旧进程）"),
        ("云枢智能 服务状态.lnk", "--status", "弹窗查看 15 个服务的端口探活结果"),
    ]
    ps = ["$ErrorActionPreference = 'Stop'", "$ws = New-Object -ComObject WScript.Shell"]
    for name, arg, desc in items:
        link = desktop / name
        ps.append(f"$sc = $ws.CreateShortcut({psq(str(link))})")
        ps.append(f"$sc.TargetPath = {psq(str(EXE))}")
        ps.append(f"$sc.Arguments = {psq(arg)}")
        ps.append(f"$sc.WorkingDirectory = {psq(str(ROOT))}")
        ps.append(f"$sc.IconLocation = {psq(str(EXE) + ',0')}")
        ps.append(f"$sc.Description = {psq(desc)}")
        ps.append("$sc.Save()")
        ps.append(f"Write-Host ('lnk -> ' + {psq(str(link))})")
    script = DIST / "make_shortcuts.ps1"
    script.write_bytes(b"\xef\xbb\xbf" + "\r\n".join(ps).encode("utf-8"))
    res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", str(script)], capture_output=True)
    text = (res.stdout or b"").decode("utf-8", "replace") + (res.stderr or b"").decode("gbk", "replace")
    print(text.strip())
    if res.returncode != 0:
        print("[失败] 快捷方式创建失败")
        sys.exit(1)
    for name, _, _ in items:
        if not (desktop / name).exists():
            print(f"[失败] 桌面缺少 {name}")
            sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="生成并安装云枢智能桌面应用")
    ap.add_argument("--no-lnk", action="store_true", help="只重建图标与 exe，不写桌面快捷方式")
    args = ap.parse_args()

    if not LAUNCHER.exists():
        print(f"[失败] 缺少 {LAUNCHER}")
        return 1

    build_icon()
    build_exe()
    if not args.no_lnk:
        desktop = desktop_dir()
        build_shortcuts(desktop)
        print(f"[桌面] {desktop}")
    print(f"[入口] pythonw {LAUNCHER} start")
    return 0


if __name__ == "__main__":
    sys.exit(main())
