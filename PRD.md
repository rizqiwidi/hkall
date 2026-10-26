# hkall — Product Requirements & Development Tracker

> Authorized security testing only. You own the consequences.

## 1. Product overview
- **Name:** hkall
- **Platform:** Android/Termux (Python 3), portable to Linux
- **Type:** modular offensive toolkit (recon, shells, C2, post-exploit, payload, net, device ops)
- **Version:** 0.3.3 (current)
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
| ops | Device ops | sub-op | termux-api battery/gps/sms/cam/mic/vibrate/clipboard |
| serve | HTTP static server | port, dir | static file staging |
| spray | Web form credential spray | url, form fields | hits logged to rs.db |
| cfg | Config / profile | key, value | persist to `config.json` |
| history | History (results store) | kind, limit | view `data/rs.db` |

## 5. Development tracker

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

## 6. Roadmap / backlog
- [ ] wifi audit (needs root/capabilities)
- [ ] persistence auto-start (termux boot / `~/.bashrc`)
- [ ] ARP scan (needs scapy or raw sockets)
- [x] banner grab → v0.3.0
- [x] .apk standalone (kotlin) — deferred
- [ ] encryption of C2 traffic (TLS) — relay XOR only placeholder
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
