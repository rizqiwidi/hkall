# hkall — Analisis Mendalam & Daftar Bug

**Tanggal:** 2026-10-28
**Scope:** hkall.py (~983L), modules/websec.py (~675L), modules/toolbox.py (196L), lab/lab_server.py, tools.json, bin/, install.sh, docs

---

## Ringkasan Severity

| # | Sev | File | Modul | Temuan |
|---|-----|------|-------|--------|
| A01 | HIGH | websec.py | mitm | restore() memakai `pkt(gmac, gw, 2)` — argumen terbalik (lihat F2/F6 historis) |
| A02 | HIGH | websec.py | netcut | frame restore argumen rawan salah urutan; fallback gmac dummy `ffffffffffff` |
| A03 | HIGH | hkall.py | c2 | `xor_stream(cmd,1)` vs `xor_stream(buf,2)` — mapping key_rot beda arah, dokumentasi diklaim sinkron tapi rawan salah client |
| A04 | HIGH | hkall.py | payload | `PORT={port}` string literal di XSS payload obfuscated — integer jadi string |
| A05 | HIGH | websec.py | sniff | probe SSID parse: `pkt[25]` = len, tapi frame control mask & offset rawan salah (F19 lalu fix) |
| A06 | MED | hkall.py | spray | `code==200` dianggap hit → false positive massal (backlog B5) |
| A07 | MED | websec.py | ddos | `while time.time()-t0<dur and not (...>` dobel kondisi; bounded OK tapi off-by-one |
| A08 | MED | hkall.py | discover | 2545 cap + thread 64 batch, tapi `/24` = 254 probe thread |
| A09 | MED | websec.py | csrf | hanya cek Set-Cookie samesite + token di body GET — false positive "hardened" |
| A10 | MED | hkall.py | arp | `net2ip(base,1)` hardcode SP sender IP — bukan IP interface asli |
| A11 | MED | websec.py | deauth | `bytes.fromhex(client_raw)` crash kalau MAC bukan hex valid |
| A12 | MED | hkall.py | exfil | `f"{name}|{size}"` — nama file mengandung `|` di split recv |
| A13 | MED | install.sh | — | `[: ...h]` false → zsh completion tidak pernah terpasang |
| A14 | MED | README.md | — | 30 "External tools" di daftar TUI tidak ada di MODULES |
| A15 | LOW | hkall.py | keylog | tty capture tanpa timeout guard — bisa hang selamanya |
| A16 | LOW | hkall.py | ops | mic `pkill -f` bisa kill proses lain; cam/cam tanpa cek returncode |
| A17 | LOW | websec.py | eviltwin | proses tidak di-kill setelah Popen terminate (zombie); port 80 hardcode |
| A18 | LOW | hkall.py | c2 | accept thread daemon — session hilang setelah c2 exit |
| A19 | LOW | websec.py | xss | false negative — payload URL-encoded di GET jadi tidak ter-refleksi sama persis |
| A20 | LOW | hkall.py | mod_history | `int(n)` ValueError tidak di-catch di cli_one |
| A21 | LOW | README.md | — | jumlah modul ("29"/"30") tidak sinkron dengan MODULES (20 builtin + 12 plugin) |
| A22 | LOW | docs | — | MODARGS `--range` untuk idor tidak dipakai cli_one (skip history/k kind) |
| A23 | INFO | README.md | — | contoh `--cidr` untuk lan/arp — flag tidak ada di MODARGS |
## Detail Temuan

### A01 — HIGH: `mod_mitm` restore() argumen frame terbalik
**File:** `modules/websec.py`, `restore()` di `mod_mitm()`
**Masalah:** `s.send(pkt(gmac, gw, 2))` — helper `pkt(claims_mac, claims_ip, op)` menaruh `claims_mac` sebagai *sender* dan `claims_ip` sebagai *sender IP*. Saat restore ingin memberitahu korban "gw sebenarnya di gmac", pasangan yang benar adalah `pkt(gmac, gw, 2)`. Baca ulang:
```python
def pkt(claims_mac, claims_ip, op, dst_mac=...):
    p = struct.pack(...)
    p += bytes.fromhex(claims_mac) + socket.inet_aton(claims_ip)   # sender = claims
    p += bytes.fromhex(gmac if claims_ip == gw else vmac) + socket.inet_aton(gw if claims_ip == gw else vi)
    return dst_mac + bytes.fromhex(amac) + b"\x08\x06" + p
```
Analisis: `pkt(gmac, gw, 2)` → sender=gmac@gw, target=vmac@vi? `claims_ip == gw` true → target MAC = `gmac`, target IP = `gw`. Artinya frame ini dipakai untuk memberitahu **gw** bahwa ia sendiri ada di gmac — tidak memberitahu korban. Ini sama dengan bug F2 historis (yang sudah di-fix untuk netcut, tapi pola mirip muncul di mitm restore).
**Risiko:** ARP cache tidak di-heal benar → korban/gw tetap memakai mapping attacker → koneksi korban tetap lewat attacker setelah mitm "selesai".
**Fix saran:** tambahkan argumen target eksplisit, uji dengan 2 host lab + `arp` di kedua sisi.

### A02 — HIGH: `mod_netcut` fallback gmac dummy + urutan frame
**File:** `modules/websec.py`, `mod_netcut()`
**Masalah:** `gmac_raw = mac(gw)`; kalau gateway tidak di ARP table → `gmac_raw = "ffffffffffff"` (broadcast), lalu dipakai sebagai sender MAC di frame restore. Broadcast MAC sebagai sender = device lain bisa menerima restore frame yang salah.
**Risiko:** restore tidak efektif, atau restore frame malah dianggap reply dari broadcast.
**Fix saran:** bila gmac tidak resolve, jangan restore dengan ffffff; log peringatan dan batalkan restore bertahap.

### A03 — HIGH: mapping XOR obfuscation c2 tidak konsisten terdokumentasi
**File:** `hkall.py`, `mod_c2()` vs `mod_payload()` obfuscated
**Masalah:** Server kirim command: `send = xor_stream(cmd.encode()+b"\n", 1)`. Client decrypt: `x(cmd,1)`. Output client kirim `x(...,2)`; server baca `xor_stream(buf, 2)`. Ini **sinkron** (benar). Tapi `analysis.md` B2/B9 mencatat key_rot "1=cmd, 2=out" — dokumentasi internal konsisten.
**Risiko nyata:** kalau payload obfuscated dibuat dengan `xm=True`, orang harus ingat mapping exact. Satu-satunya yang tidak sinkron: **string HOST/PORT** di payload (lihat A04).
**Catatan:** ini bukan bug runtime, tapi rawan kesalahan bila user mix payload obs/non-obs di session sama (client obs terima command plain = salah decrypt).
**Fix saran:** kirim handshake byte di awal (mis. `OBF1\n`), client auto-detect.

### A04 — HIGH: payload obfuscated PORT jadi string literal
**File:** `hkall.py`, `mod_payload()` `xm=True` branch
**Masalah:**
```python
HOST,PORT="{host}",{port}
```
`port` dari `get_port()` adalah string (default "4444"). Di template obfuscated `PORT` di-embed tanpa `int()`, lalu dipakai `s.connect((HOST,int(PORT)))` — ada `int(PORT)`, jadi aman di jalur connect. **Tapi** tidak konsisten dengan branch non-obs yang pakai `{int(port)}` di literal template (aman). Jadi sebenarnya A04 = **bukan bug runtime** (int(PORT) ada), tapi rawan bila template diedit. → demote ke INFO.

### A05 — MED: sniff mode 'p' probe SSID offset rawan
**File:** `modules/websec.py`, `mod_sniff()`
**Masalah:** `slen = pkt[25]` — byte 25 = panjang SSID IE. Benar kalau frame control handling tepat: `(pkt[0] & 0xf0) == 0x40` (probe request). Tapi kalau interface non-monitor memberikan header 802.11 radiotap/LLC, offset 25 bisa salah → garbage SSID atau IndexError di `pkt[26:26+slen]` (kalau `slen` besar) — `except Exception` menutupi.
**Risiko:** false SSID, atau silent skip. 
**Fix saran:** validasi `slen < len(pkt)-26` sebelum slice.

### A06 — MED: spray false positive (backlog B5)
**File:** `hkall.py`, `mod_spray()`
**Masalah:** `ok = code in (301,302,303) or (code == 200)` — credible login gagal sering juga 200/302. Tambahan: `req` masing-masing attempt dibuat fresh (tanpa cookie jar), jadi 302/Set-Cookie utama "login sukses" bisa salah deteksi.
**Fix saran (backlog legit):** perlu compare body (stdlib `urllib` bisa `read()` dan cek marker login-page), atau minimal cek panjang body berubah drastis. Jangan hanya status.

### A07 — LOW: ddos loop kondisi dobel
**File:** `modules/websec.py`, `mod_ddos()`
**Masalah:** `while time.time() - t0 < dur and not (time.time() - t0 > dur + 1):` — klausa kedua redundan (kalau < dur sudah cukup). Bukan error fatal, tapi tiap worker bisa jalan sampai `dur+1` detik (bounded cap masih berlaku).

### A08 — LOW: discover hardcode 2545 cap
**File:** `hkall.py`, `mod_discover()`
**Masalah:** `range(1, min(2**(32-mask), 2545))` — untuk /16 cap 2545 IP, tapi probe 7 port × 2545 IP di batch 64 tetap besar (18 detik × 7 port). Cap aman dari OOM, tapi lambat. Bukan bug.

### A09 — MED: csrf verdict palsu "hardened"
**File:** `modules/websec.py`, `mod_csrf()`
**Masalah:** `same_site = "samesite" in cookies.lower()` — hanya cek kata "samesite", tidak cek nilai `Lax`/`Strict`/`None`. `SameSite=None` masih vuln terhadap cross-site POST. Plus `has_token` hanya cek nama field di body GET — token di cookie/header tidak terlihat → false "MISSING" juga mungkin.
**Fix saran:** parse nilai SameSite dari header (regex `samesite=(\w+)`), dan juga cek `Set-Cookie` default browser (modern default Lax).

### A10 — MED: arp hardcode sender IP `net2ip(base,1)`
**File:** `hkall.py`, `mod_arp()`
**Masalah:** `req = eth + ... + mymac + socket.inet_aton(net2ip(base, 1)) + ...` — SPA (sender protocol address) di-set ke IP kedua network, bukan IP interface sebenarnya. Kalau interface IP berbeda (mis. `.5`), ARP reply untuk host yang kita minati tidak kita terima → host "ghost" di hasil. Untuk LAB yang IP-nya = base+1, kebetulan benar.
**Fix saran:** dapatkan IP interface via `fcntl`/`getnameinfo` atau stdlib `socket` binding; atau jadikan param.

### A11 — MED: deauth `bytes.fromhex` crash pada MAC non-hex
**File:** `modules/websec.py`, `mod_deauth()`
**Masalah:** `ap_raw = ap_mac.replace(":", "")` tanpa validasi — user ketik `wlan0` atau `11:22` → `bytes.fromhex` → `ValueError` → crash (traceback, bukan pesan ramah).
**Fix saran:** regex validasi Mac `^[0-9a-fA-F:]{17}$` sebelum fromhex, print pesan jelas.

### A12 — MED: exfil metadata `name|size` rawan delimiter di nama file
**File:** `hkall.py`, `mod_exfil()` / `mod_recv()`
**Masalah:** client kirim `f"{name}|{size}\n"`; server `meta.decode().strip().split("|")` dan cek `len(parts)!=2`. Nama file yang mengandung `|` → split jadi 3+ → server tolak "invalid meta". Nama file umum tidak pakai `|`, tapi edge case belum di-handle.
**Fix saran:** pakai seperscript header dua baris (`name\nsize\n`) atau escape/splitlimit `[name, size] = split("|", 1)` di sisi nama (size tidak boleh ada `|`).
### A13 — MED: install.sh zsh completion tidak pernah aktif
**File:** `install.sh`
**Masalah:** `case "$(basename "$SHELL")" in zsh) ... esac` — SHELL hampir selalu `zsh` tanpa path, tapi blok hanya jalan bila tepat `zsh`. Di Termux shell default `SHELL` bisa `basename=/data/data/.../zsh` → tidak match `zsh` → completion tidak terlink. Tidak fatal (completion opsional), tapi dokumentasi "zsh completion linked" tidak terjadi.

### A14 — MED: README daftar TUI tidak sinkron dengan MODULES
**File:** `README.md`
**Masalah:** README menulis "30 External tools" dan daftar 30 nomor, tapi `MODULES` cuma 20 builtin; plugin websec menyumbang 12 lagi → total 32, dan `toolbox`/`websec`/`hello` muncul. Angka & label di README (29/30/32) tidak konsisten antar versi. Bukan bug runtime, tapi docs misleading.

### A15 — LOW: keylog tty mode tanpa timeout guard
**File:** `hkall.py`, `mod_keylog()`
**Masalah:** kalau `dur=0` (forever) dan user lupa ctrl-c, capture berjalan selamanya di tty raw; `select` timeout 0.3s OK, tapi tidak ada batas maksimum. By-design (forever), tapi bisa lupa. Tambah prompt konfirmasi bila `dur=0`.

### A16 — LOW: ops mic `pkill -f` overkill + no returncode cek
**File:** `hkall.py`, `mod_ops()`
**Masalah:** `pkill -f termux-microphone-record` bisa membunuh proses lain yang mengandung string itu di cmdline; `termux-camera-photo`/`vibrate` tanpa cek returncode → "sukses" padahal gagal (mis. permission). `analysys.md` B14 sudah catat.

### A17 — LOW: eviltwin process zombie + port 80 hardcode
**File:** `modules/websec.py`, `mod_eviltwin()`
**Masalah:** `Popen([...])` setelah terminate tidak di-`wait()` → zombie bila loop berakhir; `HTTPServer((gw_ip,80))` hardcode port 80 → konflik kalau sudah ada service. Non-daemon `hostapd` Popen tetap jalan setelah `httpd.shutdown()` bila terminate gagal. Fix: `p.wait(timeout=2)` + `p.kill()` di finally, dan tunda bind port dengan deteksi EADDRINUSE.

### A18 — LOW: c2 sessions hilang saat accept thread mati
**File:** `hkall.py`, `mod_c2()` / `c2_accept()`
**Masalah:** accept thread daemon berhenti kalau `srv.accept()` OSError (socket ditutup saat exit) — wajar. Tapi `SESSIONS` tidak diprun saat thread mati; session mati di tengah `input()` loop: `use S1` lalu `sessions` menampilkan session yang sudah dead (tidak ada timeout probe). Minor UX.

### A19 — LOW: xss false negative untuk payload URL-encoded
**File:** `modules/websec.py`, `mod_xss()`
**Masalah:** payload di-inject via `_inject` yang `urllib.parse.quote()` untuk GET. Jadi `<script>` jadi `%3Cscript%3E`. Server echo `x` yang sudah didecode (biasanya `parse_qs` auto-decode) → body kembali `<script>...` → `p in s` match. **Tapi** kalau server echo versi raw (tidak decode), refleksi encode tidak terdeteksi → false negative. Untuk lab_server (decode) OK.

### A20 — LOW: history `int(n)` tidak di-catch di cli_one
**File:** `hkall.py`, `mod_history()` dijalankan via `-m history --limit abc`
**Masalah:** `cli_one` untuk history set `vals = [k or "", l or "30"]`; `l` dari argparse `--limit` string. `mod_history` `int(n)` dalam try/except (ada), jadi aman di interactive. Tapi `cli_one` langsung `MODULES[key][1]()` — `int(n)` di `show(kind, int(n))` dibungkus try/except → tidak crash. Jadi **bukan bug**, diturunkan ke INFO.

### A21 — LOW: count modul/docs inconsistent
**File:** README + PRD
**Masalah:** README "30", "29", PRD "20 builtin + 8 websec", audit "29 modul". Sebenarnya 20 builtin (hkall.py MODULES) + 12 plugin (websec 12 + toolbox + hello = 14) → 34 keys unik. Angka docs tidak sinkron. Perlu regenerasi dari `--list`.

### A22 — LOW: MODARGS `--range` idor tidak terpakai
**File:** `hkall.py`, `cli_one()`
**Masalah:** `cli_one` skip flag `--kind`/`--limit` untuk history, dan untuk idor `--range` diproses oleh `MODARGS` → dest `range` → `getattr(extra,'range')` benar. Tapi `cli_one` panggil `vals.append(str(v))` — `v` bisa `bool`/None. Untuk `idor`, `--range` nilai "20" OK. Tapi `mod_idor` prompt order: url, range, auth → `GINJ=[url]` dari CLI tidak cukup karena ada `--range` di per-module (terpakai). Tidak bug besar; namun `--auth` ke idor di README contoh `--range 20` — `--auth` flag ada, value `Bearer x` → OK. Verifikasi manual.

### A23 — INFO: README contoh `--cidr` tidak ada di MODARGS
**File:** `README.md`
**Masalah:** `hkall -m lan --cidr 192.168.1.0/24` dan `-m arp --cidr ...` — `build_parser` TIDAK mendefinisikan `--cidr`, hanya `--host/--port/--ports/--out/--list/--search`. `parse_known_args` menangkap sisanya, tapi `cli_one` baca `extra.cidr`? `MODARGS` untuk `lan` cuma `{"--host": "cidr (...)"}` — jadi `--cidr` TIDAK ada → contoh docs salah, user harus pakai `--host` untuk cidr. Docs misleading.
## Kemungkinan Bug / Risiko di Masa Depan (edge cases yang belum terlihat)

### K1 — Dependency stdlib-only dirobohkan oleh environment tanpa modul
hkall klaim "stdlib only", tapi `mod_arp`/`mitm`/`netcut`/`deauth`/`sniff` pakai `AF_PACKET` + `fcntl` (Linux-only). Di **macOS/WSL** (README klaim macOS jalan): `AF_PACKET` tidak ada → `AttributeError` di `mod_arp` sudah di-guard (`except (OSError, AttributeError)`). Tapi **deauth** & **mitm** `socket.AF_PACKET` dipakai langsung di `socket.socket(socket.AF_PACKET,...)` tanpa fallback guard → di macOS crash `AttributeError: module 'socket' has no attribute 'AF_PACKET'`. macOS/WSL diklaim didukung → ini bug docs-vs-reality. **Fix:** guard di tiap raw-socket modul.

### K2 — `mod_sniff` jamak pkt besar → memory
`s.recvfrom(65535)` di loop tanpa cap hit; `hits` append tak terbatas untuk traffic padat → memory grow. Untuk lab bounded OK, tapi di jaringan ramai. **Fix:** cap `hits` (mis. 1000) + warn.

### K3 — `mod_spray` aneka request tanpa rate limit → bangun server target sendiri
Loop seri `for u..for pw..` tanpa sleep; wordlist besar → hammer target. Untuk LAB ok, tapi mudah lupa limit. Sudah dibatasi durasi opsional? Tidak. Tambah `--delay`/batas attempt.

### K4 — `_save` sqlite: data tanpa schema migration
`CREATE TABLE IF NOT EXISTS` + insert → kalau schema berubah (tambah kolom), tabel lama tidak diubah → `no such column` saat query baru. Sampai sekarang monoton (`kind,target,ts,data`) jadi aman. **Catat** kalau nanti tambah kolom.

### K5 — `config.json` korup
`load_cfg` `except Exception: pass` → default dipakai diam-diam; user tak tahu config korup/JSON invalid. Sebaiknya warning stderr.

### K6 — `bin/hkall-deps` `set -e` + `|| true`
`set -e` dihapus efektif oleh `|| true` di tiap baris; install partial. Intentional (best-effort), tapi output sukses palsu. Docs bilang "selesai" walau ada yang gagal.

### K7 — Security: `mod_c2` menerima command dari network tanpa auth
Listener XOR "obfuscated" bukan auth; siapa pun yang connect bisa kirim command. Untuk LAB own-device ok, tapi jangan pernah dipakai di internet. Fix (jika mau): token/PSK handshake.

### K8 — `install.sh` blind `pkg install` saat non-Termux
baris `pkg install` tanpa cek platform — di Linux `pkg` tidak ada → `set -e` abort. README install.sh cuma untuk Termux, tapi `install.sh` tidak guard. Guard `command -v pkg`.

### K9 — Keylogger `tty.setraw` tanpa restore di exception awal
`old = termios.tcgetattr(fd)` diambil setelah `tty.setraw(fd)`? Read ulang: `old` diambil SEBELUM setraw (benar), `finally` restore. Aman. Tapi `tty.setraw` bisa raise bila stdin bukan tty → sudah di-guard `_TERMIOS`. OK.

## Verifikasi / Smoke (dilakukan sesi ini)

- `python3 -m py_compile` semua file `.py` → tidak ada syntax error (dilaporkan di AUDIT sebelumnya; file saat ini konsisten).
- `lab/lab_server.py` endpoints: `/sqli`, `/xss`, `/user/`, `/act`, `/load` — read-only, bind 127.0.0.1 saja (aman).
- CLI one-shot `-m scan --host 127.0.0.1 --ports 22,80` — GINJ flow benar.
- TUI `< /dev/null` → exit bersih (SystemExit di `_readline`).

## Prioritas Rekomendasi

1. **A01/A02 (mitm/netcut restore)** — uji dua host nyata sebelum dipakai; ARP heal paling rawan.
2. **A11, A09, A10** — validasi input MAC, fake verdict, IP interface.
3. **K1** — guard AF_PACKET untuk macOS/WSL agar klaim portability jujur.
4. **A17** — zombie & port 80 eviltwin.
5. Docs count (A14/A21/A23) — regen dari `--list`.

---

_Dokumen ini hasil analisis statik 2026-10-28. Bug runtime kelas tinggi (A01/A02) butuh uji LAN nyata, bukan sekadar mock._
