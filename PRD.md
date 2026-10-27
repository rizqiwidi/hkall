# hkall — Product Requirements & Development Tracker

> Authorized security testing only. You own the consequences.

## 1. Product overview
- **Name:** hkall
- **Platform:** Android/Termux (Python 3), portable to Linux
- **Type:** modular offensive toolkit (recon, shells, C2, post-exploit, payload, net, device ops)
- **Version:** 0.5.0 (current)
- **Repo:** https://github.com/rizqiwidi/hkall

## 2. Requirements
- Python 3 (stdlib only; optional `termux-api`, `netifaces`)
- Two surfaces:
  - **TUI:** `python hkall.py` → numbered menu
  - **CLI:** `python hkall.py -m MODULE [--host --port --ports]`
- Artifacts (payloads/logs/received) written to `./data/`

## 3. Architecture
- Single-file `hkall.py`: modules = functions in a `MODULES` dict
- `ask()` abstraction: interactive prompt + CLI preset queue (`GINJ`)
- `MODULES` registry: key → (name, func, interactive-flag)
- `modules/*.py` → plugin loader (`PLUGIN` dict)

## 4. Module matrix

| key | name | input | output/action |
|-----|------|-------|---------------|
| scan | Port scanner | host, ports | open list + optional banner |
| enum | Web enumerator | url | headers, mails, secrets, forms |
| whois | DNS / banner lookup | host | IPs, PTR |
| subd | Subdomain brute DNS | domain | found subdomains |
| shell | Reverse shell generator | ip, port | py/bash/nc/sh/php one-liners |
| c2 | C2 listener (multi-session) | port | interactive shell, XOR stream |
| keylog | Keylogger | duration | `data/keys.log` |
| exfil | Exfil client | ip, port, file | send file to recv server |
| recv | Exfil server | port | file → `data/` |
| payload | Android payload builder | ip, port | `data/payload.py` (reconnect + XOR) |
| exe2 | Shell payload variants | ip, port | termux am / linux one-liner |
| lan | LAN host discoverer | cidr | hosts up (7-port probe) |
| arp | ARP scan (root) | cidr | MAC/IP live hosts (AF_PACKET) |
| wifi | Wifi audit | — | scaninfo + connectioninfo |
| persist | Persistence | on-boot cmd | boot script + bashrc hook |
| ops | Device ops | sub-op | termux-api battery/gps/sms/cam/mic/vibrate/clipboard |
| serve | HTTP static server | port, dir | static file staging |
| spray | Web form credential spray | url, form fields | hits logged to rs.db |
| cfg | Config / profile | key, value | persist to `config.json` |
| history | History (results store) | kind, limit | view `data/rs.db` |
| sqli | SQLi tester (plugin) | url | 16-payload classic+time diff, issues |
| xss | XSS reflection check (plugin) | url | raw-reflected payload list |
| csrf | CSRF check (plugin) | url | SameSite/token verdict |
| idor | IDOR enumeration (plugin) | api url + range | accessible IDs |
| mitm | ARP MITM lab (plugin) | victim/gw/iface | ARP spoof + auto-restore |
| dnsspoof | DNS spoof lab (plugin) | port/domain/ip | fake DNS server |
| ddos | Load test (plugin) | url/conn/dur | req/s + byte stats |
| websec | Orchestrator menu (plugin) | category | chained web tests |
| toolbox | External tools launcher (plugin) | category/tool | run sqlmap/nmap/hydra/ffuf/bettercap/dnschef/tcpdump via `tools.json` |

## 5. Development tracker

### v0.5.0 (2026-10-27) — multi-platform + full tool catalog (24 tools)
- [x] `tools.json` → **24 tool**: +dalfox, xsstrike, feroxbuster, responder, mhddos (guide), loic (guide)
- [x] `bin/hkall-deps` — bootstrap cross-platform: detect Termux→pkg / Linux→apt/dnf/pacman / pip / Go source
- [x] `tools.json` 18 tool exported — semua muat platform (nmap/hydra/ffuf/bettercap/dnschef/mitmproxy/hping3/dnsmasq/dsniff/ab/siege/wrk/goldeneye/macchanger)
- [x] toolbox.py rewrite platform-agnostic: `_detect_pm()` (pkg/apt/dnf/pacman/pip), `_install_cmd` per pm, md_only/guide handling, `_pkg_available` platform-aware
- [x] terverifikasi: 24 tool, `--list` 20 builtin + plugin, sqli/csrf/idor/csrf one-shot final OK, py_compile + sh -n OK

### v0.4.3 (2026-10-27) — full inventory audit + lab + comprehensive docs


- [x] audit inventaris: 29 modul aktif (20 builtin + 8 websec + toolbox) diverifikasi via `--list`
- [x] `lab/lab_server.py` masuk repo — vulnerable lab (sqli/xss/user/act/load) buat latihan device sendiri, semua modul web terverifikasi terhadapnya
- [x] `docs/USAGE.md` full rewrite: 27+ modul + 18 tool + alur belajar lengkap + contoh CLI per modul (pakai `hkall` global)
- [x] `--help` hint saat `HKALL_NOPLUGIN` menyembunyikan plugin
- [x] typo fix + py_compile semua modul OK
- [ ] encrypted C2 (TLS) — backlog

### v0.4.2 (2026-10-27) — global CLI framework + TUI search/info + completion
- [x] `bin/hkall` global launcher (shebang, symlink-aware), install.sh → PATH (`$PREFIX/bin` / `~/bin`)
- [x] `MODARGS` per-module CLI arg schema + `hkall -m MODULE --help` (dynamic two-phase argparse)
- [x] TUI: `/query` filter + `i N` module info; `HKALL_NOPLUGIN` silence plugin noise (fast completion)
- [x] bash + zsh completion scripts (`bin/hkall-completion.*`)
- [x] plugin `_ask` (websec/toolbox) baca `GINJ` CLI presets → `-m sqli --host ... --range 5 --auth ...` one-shot penuh
- [x] fixes: cli_one GINJ double-host bug (generic --host + MODARGS --host dobel), phase-1 parse_known_args for module flags
- [x] docs: README global command + completion + TUI nav, USAGE §0
- [ ] encrypted C2 (TLS) — backlog

### v0.4.1 (2026-10-27) — toolbox catalog expansion
- [x] tools.json 8 → 18 tools: +hping3, dnsmasq, dsniff, ab, siege, wrk, mitmproxy, goldeneye, macchanger
- [x] kategori baru: `load` (ab/siege/wrk/goldeneye)
- [x] toolbox `_install`: apt-cache policy check sebelum nawarkan install (no phantom packages)
- [x] verified: all 5 categories render, per-tool MISSING/ok detect correct (tshark, mitmdump = terpasang)
- [x] docs: README toolbox section (per-category table), USAGE tool table + unavailable list

### v0.4.0 (2026-10-27) — web sec modules + external toolbox
- [x] `modules/websec.py` plugin: sqli, xss, csrf, idor, mitm, dnsspoof, ddos, websec (orchestrator)
- [x] `modules/toolbox.py` plugin: external tool launcher with auto-install offer + `tools.json` catalog
- [x] verified against local lab server: sqli 16/16 detect, xss 6/6 raw-reflect, csrf verdict, idor 1-3 accessible, ddos 181 req/s
- [x] docs: `docs/USAGE.md` (alur lengkap), README (29 modules + CLI examples), PRD matrix + tracker
- [x] fixes: `_http_req` HTTPError status passthrough (4xx/5xx are signal), sqli base-status compare, lab query decode
- [ ] external binaries install (user declined on this device — toolbox offers on demand)
- [ ] encrypted C2 (TLS) — still backlog

### v0.1.0 (2026-10-24) — initial
- [x] core app + 8 modules (scan, enum, shell, c2, keylog, exfil client/server, payload)
- [x] packaged to GitHub repo `rizqiwidi/hkall`
- [ ] APK standalone (kotlin) — deferred, needs PC + gradle

### v0.2.0 (2026-10-24) — TUI + CLI + ops
- [x] TUI menu (colored, numbered)
- [x] one-shot CLI via argparse (`-m MODULE` + flags)
- [x] termux-api ops module with graceful detection
- [x] module count 8 → 12 (added whois, exe2, lan, ops)

### v0.2.1 (2026-10-24) — fixes
- [x] removed dead code (`_net_interface`, unused imports, garbled py2exe)
- [x] mod_discover probes 7 common ports; CIDR validation
- [x] clean mod_py2exe output

### v0.3.0 (2026-10-24) — storage, multi-session C2, config, plugins
- [x] sqlite result store `data/rs.db` + `history` module
- [x] `--out` save support
- [x] C2 multi-session (sessions/use/kill) with XOR stream obfuscation
- [x] config profiles `config.json` (persist via `cfg` module)
- [x] plugin loader (`modules/*.py` → `PLUGIN` dict) + sample `hello`
- [x] banner grab in scan (per open port, optional)
- [x] ops auto-exec (run-all snapshot)
- [ ] encrypted C2 (TLS) — backlog

### v0.3.1 (2026-10-24)
- [x] fix NameError (registry before defs), rewrite clean single-registry
- [x] add subdomain brute, c2 non-tty guard, remove dead db()

### v0.3.2 (2026-10-26) — polish + missing files
- [x] fix payload XOR obfuscated inline script (broken `x()` call, shell-cmd executor)
- [x] add `wordlist.txt` (password wordlist for spray module)
- [x] rewrite install.sh (git pull on re-run, v0.3.2 echo)
- [x] extend .gitignore (*.log, *.db, *.apk, *.m4a, *.jpg, wordlist.txt)
- [x] rewrite README.md (all 18 modules documented, CLI examples, C2 usage, plugin guide)
- [x] update PRD.md (v0.3.1 + v0.3.2 changelog, module matrix complete)
- [ ] encrypted C2 (TLS) — still backlog

### v0.3.3 (2026-10-26) — deep audit fixes
- [x] payload non-obs: correct shell path (`/system/bin/sh` → `/bin/sh` → `sh`) + reconnect
- [x] payload obs: remove dead `r()`; indent fixed; syntax verified
- [x] recv: path traversal sanitized (`basename`), no infinite loop on empty meta
- [x] c2: BrokenPipe/closed-session guards (no crash on dead session)
- [x] discover: thread cap batch 64 (was 254 at once)
- [x] plugin loader: warn+skip key shadowing builtin
- [x] history: table auto-created on show (no crash on empty db)
- [ ] spray success detection (code-based only → false positives) — backlog

### v0.3.4 (2026-10-26) — new modules: wifi, persist, arp
- [x] `wifi` module — termux-api scaninfo + connectioninfo
- [x] `persist` module — opt-in boot script + `~/.bashrc` hook
- [x] `arp` module — raw socket AF_PACKET ARP sweep (root, Linux)
- [x] registry 18 → 21 modules
- [x] README updated (21 modules)
- [x] PRD module matrix + roadmap updated

## 6. Roadmap / backlog
- [x] wifi audit (termux-api scaninfo/connectioninfo) → v0.3.4
- [x] persistence auto-start (termux boot / `~/.bashrc`) → v0.3.4
- [x] ARP scan (AF_PACKET, root) → v0.3.4
- [x] banner grab → v0.3.0
- [ ] .apk standalone (kotlin) — needs PC + gradle
- [ ] encrypted C2 traffic (TLS) — relay XOR placeholder
- [x] modules/ dir plugin loading → v0.3.0
- [x] sqlite results store → v0.3.0
- [x] config profiles → v0.3.0
- [x] multi-session C2 → v0.3.0

## 7. Changelog
- 2026-10-24 v0.1.0 initial (8 modules)
- 2026-10-24 v0.2.0 TUI + CLI + ops (12 modules)
- 2026-10-24 v0.2.1 fixes
- 2026-10-24 v0.3.0 storage + multi-session C2 + config + plugins (14+ modules)
- 2026-10-24 v0.3.1 fix NameError + add subd brute + c2 guard
- 2026-10-26 v0.3.2 payload XOR fix, wordlist, install.sh fix, README rewrite
- 2026-10-26 v0.3.3 deep-audit fixes: payload shell path, recv traversal+hang guard, c2 session guards, discover thread cap, plugin shadow warn, history empty-db
- 2026-10-26 v0.3.4 wifi + persist + arp modules (21 total)
