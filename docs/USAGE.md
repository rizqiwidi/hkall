# hkall — Usage & Alur (Menu → Input → Auto)

Semua modul di sini: **uji device/network milik sendiri saja.** Belajar, bukan target pihak ketiga.
Alur umum (TUI): `python hkall.py` → menu numbered → pilih nomor modul → jawab prompt → hasil otomatis
tersimpan ke `data/rs.db` (bisa ditarik lewat modul `history`).

Alur CLI one-shot: `python hkall.py -m MODULE [--host --port --ports]` (prompt dilewati preset).

---

## 1. Web vuln (sqli, xss, csrf, idor)

### sqlmap (best-in-class) — automated
```
pkg install sqlmap          # Termux
python hkall.py -m websec   # pilih "SQLi via sqlmap"
# tetap manual: sqlmap -u "http://DEVICE/sqli.php?x=1" --batch --level 3 --risk 2 --dbs
```
- Input: url target (device sendiri), method, param.
- Output: database list `--dbs`, tabel `--tables`, dump `--dump`.

### Internal sqli (pure python, no dep)
`python hkall.py -m sqli` → target url → otomatis test 16 payload classic + time-based, catat status/timing differ.

### xss
`python hkall.py -m xss` → url param → 6 payload kunci → cek reflected/escaped.
Pingin lebih dalam: `xsstrike` / `dalfox` taruh path, modul websec akan pakai binary kalau tersedia (dual-path).

### csrf
`python hkall.py -m csrf` → url → cek SameSite cookie + token body + verdict hardened/review.

### idor
`python hkall.py -m idor` → api url (`/user/{{id}}`) → range ID → auth header opsional → cek tiap id bukan 404.
Lanjut Otomatis: `ffuf -u http://DEVICE/FUZZ` buat path, `burp` manual.

---

## 2. Network (mitm, dns spoof)

### bettercap (kalau terpasang) — warnings: root + restore
```
pkg install bettercap   # Termux, repo root
sudo bettercap -iface wlan0
# caplet: arp.spoof + dns.spoof (lab)
set arp.spoof.targets 192.168.1.50   # device kedua (milikmu)
arp.spoof on
dns.spoof on
dns.spoof.domains test.lab
dns.spoof.address 127.0.0.1
```
Aku tandai design constraint: modul `mitm` internal sudah auto-restore ARP on exit, jadi aman di perangkat sendiri. `dnsspoof` internal pakai fake DNS server.

### fallback internal
- `python hkall.py -m mitm` → root → vi/gw/iface/seconds → ARP spoof, restore cache otomatis.
- `python hkall.py -m dnsspoof` → root → port/domain/ip → fake DNS server jawab `test.lab -> ip`, stop ctrl-c.

---

## 3. Load test (bddos)

`python hkall.py -m ddos` → url (device sendiri) → concurrency (cap 200) + duration (cap 60s) → req/s + byte.

Untuk lebih realistis (local only): `ab -n 1000 -c 50 http://127.0.0.1:8090/load`, atau `wrk`/`vegeta` kalau terpasang.
`ab` tersedia di Android via `pkg install apache2-utils`.

---

## 4. Alur lengkap (contoh belajar device sendiri)

1. Bikin lab server di device sendiri (tempat uji):
   ```
   git clone ... ; cd hkall; python3 -m http.server 8090   # atau /tmp/lab_server.py
   ```
2. `python hkall.py` → menu → `sqli` → target `http://127.0.0.1:8090/sqli` → hasil.
3. `xss` → `http://127.0.0.1:8090/xss` → reflected.
4. `idor` → `http://127.0.0.1:8090/user/{{id}}` → range 1-5 → dapat id 1-3.
5. `csrf` → `http://127.0.0.1:8090/act` → verdict review (no token).
6. `ddos` → `http://127.0.0.1:8090/load` → 20 conn 10s → req/s.
7. Cek hasil: `python hkall.py -m history` → semua tersimpan di `rs.db`.

---

## 5. External tools (`toolbox`)

`python hkall.py -m toolbox` → menu kategori (web / net / recon / auth / load) → pilih tool → kalau binary
belum ada, toolbox tawarkan `pkg install` (cek dulu ketersediaan repo, butuh konfirmasi kamu) → wrapper
interaktif → jalan.

Katalog: `tools.json` (18 tool). Tool yang didukung:

| tool | pkg | kategori | butuh root | status device ini |
|------|-----|----------|-----------|-------------------|
| sqlmap | sqlmap | web | tidak | MISSING |
| ffuf | ffuf | web | tidak | MISSING |
| mitmproxy | mitmproxy | web | transparent mode | **terpasang** (`mitmdump`) |
| bettercap | bettercap | net | ya | MISSING |
| dnschef | pip | net | ya | MISSING |
| tcpdump | tcpdump | net | ya | MISSING |
| tshark | (sudah ada) | net | ya | **terpasang** |
| hping3 | hping3 | net | ya | MISSING |
| dnsmasq | dnsmasq | net | tidak (pakai -p 5353) | MISSING |
| dsniff | dsniff | net | ya | MISSING |
| macchanger | macchanger | net | ya | MISSING |
| nmap | nmap | recon | tidak | MISSING |
| hydra | hydra | auth | tidak | MISSING |
| ab | apache2-utils | load | tidak | MISSING |
| siege | siege | load | tidak | MISSING |
| wrk | wrk | load | tidak | MISSING |
| goldeneye | goldeneye | load | tidak | MISSING |
| ettercap | — | net | ya | unavailable (bukan di repo Termux) |

Tidak di repo Termux, butuh source/pip: `dalfox`, `xsstrike`, `feroxbuster` (XSS/IDOR fuzz).
GUI/cloud, tidak cocok Termux CLI: `Burp Suite`, `XSSHunter`, `evilginx`. Windows-only: `responder`.

---

## Struktur menu saat ini (21 builtin + 9 plugin)

| key | name |
|-----|------|
| scan/enum/whois/subd | recon |
| shell/c2/payload/exe2/keylog | shells |
| exfil/recv | exfil |
| lan/arp/wifi | network |
| persist/ops/serve/spray/cfg/history | misc |
| **sqli/xss/csrf/idor** | **web vuln** |
| **mitm/dnsspoof** | **network attack lab** |
| **ddos** | **load test** |
| **websec** | **orchestrator menu** |
| **toolbox** | **external tools (sqlmap/nmap/hydra/ffuf/bettercap/dnschef/tcpdump)** |

Default yang aman tetap: semua bertarget device sendiri, modul mitm/dnsspoof butuh root dan restore otomatis.
