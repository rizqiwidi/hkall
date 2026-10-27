#!/usr/bin/env python3
"""hkall toolbox — unified launcher for external offensive tools.
Reads tools.json; checks binary; offers install; runs with interactive arg prompts.
LAB/OWN-DEVICE USE ONLY."""
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
    try:
        v = input(prompt + " ").strip()
        return v or default
    except (EOFError, KeyboardInterrupt):
        return default

def _yn(prompt):
    return _ask(prompt, "n").strip().lower() in ("y", "yes", "1", "true")

def _have(binname):
    return shutil.which(binname) is not None

def _install(tool):
    """Offer + run install. Returns True if tool becomes available."""
    name = tool.get("bin")
    pkg = tool.get("pkg")
    pip = tool.get("pip")
    if tool.get("unavailable"):
        print(f"{name}: not packaged for Termux — skipped"); return False
    print(f"\n{name} is NOT installed.")
    if pkg:
        if _yn(f"Install via pkg install {pkg}? (needs network, ~y/N) "):
            print(f"$ pkg install {pkg}")
            subprocess.run(["pkg", "install", "-y", pkg])
            return _have(name)
    if pip:
        if _yn(f"Install via pip install {pip}? "):
            print(f"$ pip install {pip}")
            subprocess.run([sys.executable, "-m", "pip", "install", pip])
            return _have(name)
    print("skipped install — using internal fallback if any")
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
            if flag == "target":
                argv.append(v)
            elif flag == "service":
                argv.append(v)
            elif flag == "filter":
                argv.append(v)
            elif flag.startswith("-"):
                argv.extend([flag, v])
            else:
                argv.append(v)
    return argv

def _run(tool, argv):
    print("\n$ " + " ".join(argv))
    if tool.get("needs_root") and hasattr(os, "geteuid") and os.geteuid() != 0:
        print("warning: this tool wants root (run 'tsu' first) — trying anyway")
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
        print("toolbox is interactive; run from a tty. use -m scan/nmap-style modules instead")
        return
    print("detected: " + (", ".join(t["bin"] for t in tools.values() if _have(t.get("bin"))) or "none"))
    # group by category
    by_cat = {}
    for key, t in tools.items():
        if t.get("unavailable"): continue
        by_cat.setdefault(t.get("cat", "misc"), []).append((key, t))
    order = list(by_cat)
    for i, c in enumerate(order, 1):
        print(f"{i}. {c} — {cats.get(c, '')}")
    sel = _ask("category:", "1")
    try: c = order[int(sel) - 1]
    except (ValueError, IndexError): print("bad"); return
    items = by_cat[c]
    for i, (key, t) in enumerate(items, 1):
        mark = "ok" if _have(t["bin"]) else "MISSING"
        print(f"  {i}. {key:10} [{mark}] {t['desc']}")
    sel2 = _ask("tool:", "1")
    try: key, tool = items[int(sel2) - 1]
    except (ValueError, IndexError): print("bad"); return
    binname = tool["bin"]
    if not _have(binname):
        if not _install(tool):
            print(f"{binname} unavailable — try internal module (see --list)")
            return
    binpath = shutil.which(binname)
    argv = _build_cmd(tool, binpath)
    if not _ask("run? [Y/n] ", "y").startswith("n"):
        _run(tool, argv)

PLUGIN = {"toolbox": ("External tools launcher (sqlmap/nmap/hydra/ffuf/bettercap/...)", mod_toolbox, True)}
