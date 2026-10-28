#!/usr/bin/env python3
"""hkall toolbox — unified launcher for external offensive tools.
Reads tools.json; checks binary; offers platform-aware install; runs with interactive arg prompts.
Platform: Termux (pkg), Linux (apt/dnf/pacman), pip, or source build. LAB/OWN-DEVICE USE ONLY."""
import os, sys, json, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "tools.json")

def _load():
    try:
        with open(CATALOG) as f: return json.load(f)
    except Exception as e:
        print(f"catalog error: {e}"); return {"tools": {}, "categories": {}}

def _banner(t): print(f"\n== {t} ==")

def _ask(prompt, default=""):
    # CLI preset queue from hkall main (set by cli_one for -m MODULE presets)
    try:
        import __main__ as _m
        q = getattr(_m, "GINJ", None)
        if q:
            return str(q.pop(0))
    except Exception:
        pass
    try:
        v = input(prompt + " ").strip()
        return v or default
    except (EOFError, KeyboardInterrupt):
        return default

def _yn(prompt):
    return _ask(prompt, "n").strip().lower() in ("y", "yes", "1", "true")

def _have(binname):
    return bool(binname) and shutil.which(binname) is not None

def _is_termux():
    return bool(os.environ.get("PREFIX", "").startswith("/data/data/com.termux")) or os.path.isdir("/data/data/com.termux")

def _detect_pm():
    """Package manager per platform."""
    if _is_termux():
        return "pkg" if shutil.which("pkg") else "apt-get"
    if shutil.which("apt-get"): return "apt-get"
    if shutil.which("dnf"): return "dnf"
    if shutil.which("pacman"): return "pacman"
    return "pip"

def _pkg_available(pkg):
    """Cek paket ada di repo sebelum nawarkan install (apt/pacman/dnf dihindari, pkg cek)."""
    pm = _detect_pm()
    try:
        if pm == "pkg":
            r = subprocess.run(["apt-cache", "policy", pkg], capture_output=True, text=True, timeout=10)
            for line in r.stdout.splitlines():
                if line.strip().startswith("Candidate:"):
                    cand = line.split(":", 1)[1].strip()
                    return cand and cand != "(none)"
        return True  # platform pm: cukup tawarkan, user yang putuskan
    except Exception:
        return True

def _install_cmd(pm, pkg):
    """Return argv list untuk install paket via pm."""
    if pm == "pkg":
        return ["pkg", "install", "-y", pkg]
    elev = "" if (hasattr(os, "geteuid") and os.geteuid() == 0) else ("sudo " if shutil.which("sudo") else "")
    if pm == "apt-get":
        return (elev + "apt-get install -y " + pkg).split()
    if pm == "dnf":
        return (elev + "dnf install -y " + pkg).split()
    if pm == "pacman":
        return (elev + "pacman -S --noconfirm " + pkg).split()
    return [sys.executable, "-m", "pip", "install", pkg]

def _install(tool):
    """Platform-aware install. Returns True if tool becomes available."""
    name = tool.get("bin") or tool.get("pip") or tool.get("pkg")
    if tool.get("md_only"):
        print(f"{name}: guide-only — cara pakai di docs/USAGE.md dan README."); return False
    if tool.get("unavailable") and not _is_termux():
        # unavailable hanya untuk Termux; di Linux bisa coba
        pass
    pkg = tool.get("pkg")
    pip = tool.get("pip")
    src = tool.get("src")
    if not (pkg or pip or src):
        print(f"{name}: tanpa metode install otomatis — baca docs (build manual dari source)."); return False
    print(f"\n{name} is NOT installed.")
    if pip:
        if _yn(f"Install via pip install {pip}? "):
            print(f"$ {sys.executable} -m pip install {pip}")
            subprocess.run([sys.executable, "-m", "pip", "install", pip])
            return _have(name)
    elif pkg:
        pm = _detect_pm()
        if pm == "pip" or not _pkg_available(pkg):
            if pm == "pip":
                print(f"no system package manager — pakai pip: {sys.executable} -m pip install {pkg}")
            else:
                print(f"paket '{pkg}' tidak ditemukan di repo {pm}")
        elif _yn(f"Install via {pm} install {pkg}? "):
            print(f"$ {' '.join(_install_cmd(pm, pkg))}")
            subprocess.run(_install_cmd(pm, pkg))
            return _have(name)
    if src:
        if _yn(f"Build via: {src}? "):
            print(f"$ {src}")
            subprocess.run(src, shell=True)
            return _have(name)
    print("skipped install — pakai internal fallback (lihat --list) kalau ada")
    return False

def _build_cmd(tool, binpath):
    """Interactive arg build from catalog schema. Returns argv list."""
    argv = [binpath]
    for a in tool.get("args", []):
        flag = a.get("flag", "")
        prompt = a.get("prompt", flag)
        if a.get("const"):
            argv.append(flag); continue
        if a.get("bool"):
            if _yn(prompt + " "):
                argv.append(flag)
            continue
        d = a.get("default", "")
        v = _ask(prompt + (" [%s]" % d if d else "") + ":", d)
        if v:
            # positional/flag dispatch
            if flag.startswith("--"):
                # long --flag: needs --flag value
                argv.extend([flag, v])
            elif flag.startswith("-") and flag != "-":
                # short -X or bundled -iface/-eval etc: keep as flag+value
                argv.extend([flag, v])
            else:
                # bare non-flag arg (positional, no dash, e.g. target/service)
                argv.append(v)
    return argv

def _run(tool, argv):
    print("\n$ " + " ".join(argv))
    if tool.get("needs_root") and hasattr(os, "geteuid") and os.geteuid() != 0:
        print("warning: tool ini butuh root (parting tsu/sudo di termux) — coba tetap")
    try:
        subprocess.run(argv)
    except KeyboardInterrupt:
        print("\ninterrupted")
    except Exception as e:
        print(f"run error: {e}")

def mod_toolbox():
    """Menu: category -> tool -> install if missing -> interactive run."""
    cat = _load()
    tools = cat.get("tools", {})
    cats = cat.get("categories", {})
    _banner("TOOLBOX (external tools launcher)")
    if not sys.stdin.isatty():
        print("toolbox is interactive; run from a tty. gunakan -m MODULE (lihat --list)")
        return
    detected = [t["bin"] for t in tools.values() if _have(t.get("bin"))]
    print("detected: " + (", ".join(detected) if detected else "none"))
    # group by category, skip md_only + visible guide-only tools
    by_cat = {}
    for key, t in tools.items():
        if not key or t.get("hidden"):
            continue
        by_cat.setdefault(t.get("cat", "misc"), []).append((key, t))
    order = list(by_cat)
    for i, c in enumerate(order, 1):
        print(f"{i}. {c} — {cats.get(c, '')}")
        for j, (key, t) in enumerate(by_cat[c], 1):
            mark = "ok" if _have(t.get("bin")) else ("guide" if t.get("md_only") else "MISSING")
            print(f"   {j}. {key:10} [{mark}] {t['desc']}")
    sel = _ask("category:", "1")
    try: c = order[int(sel) - 1]
    except (ValueError, IndexError): print("bad"); return
    sel2 = _ask("tool:", "1")
    try: key, tool = by_cat[c][int(sel2) - 1]
    except (ValueError, IndexError): print("bad"); return
    if tool.get("md_only"):
        print(f"{key}: guide-only — cara pakai di docs/USAGE.md."); return
    binname = tool.get("bin")
    if not binname:
        print(f"{key}: tanpa binary launcher — cek docs."); return
    if not _have(binname):
        if not _install(tool):
            print(f"{binname} tidak tersedia — internal module mungkin ada (--list)")
            return
    argv = _build_cmd(tool, shutil.which(binname))
    if not _ask("run? [Y/n] ", "y").startswith("n"):
        _run(tool, argv)

PLUGIN = {"toolbox": ("External tools launcher (SQLi fuzz MITM load, multi-platform)", mod_toolbox, True)}
