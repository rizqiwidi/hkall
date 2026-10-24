# hkall

Modular offensive toolkit for Android/Termux. Use only on systems you own or have explicit permission to test.

## Install (on phone)

```bash
pkg install -y python git
git clone https://github.com/rizqiwidi/hkall.git
cd hkall
python hkall.py
```

## Modules

| # | Module | Notes |
|---|--------|-------|
| 1 | Port scanner | thread-pool TCP, range or full 1-65535 |
| 2 | Web enumerator | headers, emails, tokens, `script/iframe/form` |
| 3 | Reverse shell generator | py / bash / nc / sh one-liners |
| 4 | C2 listener | interactive shell over reverse tcp |
| 5 | Keylogger | termios raw mode, logs to `data/keys.log` |
| 6 | Exfil client | send file to listener |
| 7 | Exfil server | receive file into `data/` |
| 8 | Android payload builder | generates `data/payload.py` reconnect shell |

Generated artifacts (payloads, logs, received files) live in `data/`.

## Quick receiver (other machine)

```bash
nc -lvnp 12345            # receive a raw file (no metadata)
```

For exfil module pairing: run module 7 on the C2 server, module 6 on the target.

## Extend

Drop a new function into `hkall.py` and add it to `MENU`. Add `modules/` pack later.

## Legal

Authorized testing only. Unauthorized access is illegal in most jurisdictions — you are responsible for how this is used.
