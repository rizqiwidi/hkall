# hkall — Product Requirements & Development Tracker

> Authorized security testing only. You own the consequences.

## 1. Product overview
- **Name:** hkall
- **Platform:** Android/Termux (Python 3), portable to Linux
- **Type:** modular offensive toolkit (recon, shells, C2, post-exploit, payload, net, device ops)
- **Version:** 0.2.1 (working)
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

## 4. Module matrix

| key | name | input | output/action |
|-----|------|-------|---------------|
| scan | Port scanner | host, ports, full | open list |
| enum | Web enumerator | url | headers, mails, secrets, forms |
| whois | DNS / banner lookup | host | IPs, PTR |
| shell | Reverse shell generator | ip, port | py/bash/nc/sh/php one-liners |
| c2 | C2 listener | port | interactive shell, logs cmds |
| keylog | Keylogger | duration | `data/keys.log` |
| exfil | Exfil client | ip, port, file | send file |
| recv | Exfil server | port | file → `data/` |
| payload | Android payload builder | ip, port | `data/payload.py` reconnect shell |
| exe2 | Shell payload variants | ip, port | termux am/linux one-liner |
| lan | LAN host discoverer | cidr | hosts up (probe 22/80/135/139/443/445/3389) |
| ops | Device ops | sub-op | termux-api battery/gps/sms/cam/mic/vibrate/clipboard |

## 5. Development tracker

### v0.1.0 (2026-10-24) — initial
- [x] core app + 8 modules (scan, enum, shell, c2, keylog, exfil client/server, payload)
- [x] packaged to personal GitHub repo `rizqiwidi` — placeholder, fix owner
- [x] smoke: menu + scanner vs live port
- [ ] APK standalone (kotlin) — deferred, needs PC + gradle

### v0.2.0 (2026-10-24) — TUI + CLI + ops
- [x] TUI menu (colored, numbered, category tags)
- [x] one-shot CLI via argparse (`-m MODULE` + flags)
- [x] termux-api ops module with graceful detection
- [x] module count 8 → 12 (added whois, exe2, lan, ops)
- [x] README + install.sh updated

### v0.2.1 fixes (2026-10-24)
- [x] removed dead code (`_net_interface`, unused `json` import, garbled py2exe)
- [x] mod_discover now probes 7 common ports, not just 135; validates cidr
- [x] clean mod_py2exe output (am start + linux one-liner)
- [x] smoke all modules after fixes

## 6. Roadmap / backlog
- [ ] wifi audit (needs root/capabilities)
- [ ] persistence auto-start (termux boot / `~/.bashrc`)
- [ ] ARP scan, real banner grab
- [ ] .apk standalone (kotlin)
- [ ] encryption of C2 traffic (TLS)
- [ ] modules/ dir plugin loading

## 7. Changelog
- 2026-10-24 v0.1.0 initial (8 modules)
- 2026-10-24 v0.2.0 TUI + CLI + ops (12 modules)
- 2026-10-24 v0.2.1 fixes
