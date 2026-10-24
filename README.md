# hkall

Modular offensive toolkit for Android/Termux. Use only on systems you own or have explicit permission to test.

## v0.2.0 — What's new
- **TUI menu** (categorized, colored, numbered)
- **One-shot CLI**: `python hkall.py -m <module> [--host --port --ports]`
- **Device ops** module (`termux-api`) for battery, GPS, SMS, camera, mic, vibration, clipboard

## Install (on phone)

```bash
pkg install -y python git termux-api
git clone https://github.com/rizqiwidi/hkall.git
cd hkall
python hkall.py
```

`termux-api` is optional — needed only for module 12 (device ops).

## Interactive menu (TUI)
Run `python hkall.py` → pick a number:

| # | Module | Category |
|---|--------|----------|
| 1 | Port scanner | recon |
| 2 | Web enumerator (headers, mails, secrets, forms) | recon |
| 3 | DNS / banner lookup | recon |
| 4 | Reverse shell generator (py/bash/nc/sh/php) | shells |
| 5 | C2 listener (interactive reverse shell) | shells |
| 6 | Keylogger (termios) | post-exploit |
| 7 | Exfil client (send file) | post-exploit |
| 8 | Exfil server (receive file) | post-exploit |
| 9 | Android payload builder (reconnect shell) | payload |
| 10 | Shell payload variants | payload |
| 11 | LAN host discoverer | net |
| 12 | Device ops (termux-api) | ops |

## One-shot CLI

```bash
python hkall.py --list                      # all modules
python hkall.py -m scan --host 192.168.1.5 --ports 1-1000
python hkall.py -m scan --host x.x.x.x --ports 445,3389,8080
python hkall.py -m enum --host http://example.com
python hkall.py -m payload --host 1.2.3.4 --port 8443
python hkall.py -m launch                  # (TUI)
```

## Typical workflow
```
recon (1-3) → find open port → payload/keygen (9-10)
           → C2 listener (5) → target runs payload
           → post-exploit (6-8): keys, exfil
          (12) device ops if on termux-api device
```

## Legal
Authorized testing only. Unauthorized access is illegal — you are responsible for how this is used.
