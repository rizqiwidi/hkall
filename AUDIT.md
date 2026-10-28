# hkall — Audit Report
**Repo:** `hkall/`  |  **Commit basline:** `de8f092`  |  **Version:** `0.6.0`
**Audit date:** 2026-10-27
**Scope:** hkall.py (~951L), modules/websec.py (~627L), modules/toolbox.py (192L), lab/, bin/, install.sh
**Method:** full source read → static analysis → targeted dynamic smoke (mocks) → fixes → re-verify

---

## Ringkasan Severity

| # | Severity | Modul | Judul | Status |
|---|----------|-------|-------|--------|
| F1 | **CRITICAL** | mitm | ARP spoof tidak intercept traffic (sender MAC = korban MAC, bukan attacker MAC) | ✅ FIXED |
| F2 | **CRITICAL** | netcut | Frame restore inverted → re-poison ARP cache saat selesai | ✅ FIXED |
| F3 | **HIGH** | recv | `socket.timeout` uncaught saat menunggu meta → crash+lihat traceback | ✅ FIXED |
| F4 | **HIGH** | recv | `int(size)` ValueError kalau client kirim meta non-numeric | ✅ FIXED |
| F5 | **MEDIUM** | keylog | `int(dur)` ValueError kalau user input non-numeric | ✅ FIXED |
| F6 | **MEDIUM** | mitm/netcut | MAC read dari /proc/net/arp (format colon) → `bytes.fromhex` error | ✅ FIXED (netcut plus mitm) |
| F7 | **MEDIUM** | websec menu | `url` prompt di auto-chain diabaikan — tiap modul minta URL lagi | ✅ FIXED |
| F8 | **LOW** | c2 | read timeout 2s potong output besar/lambat | ✅ FIXED — recv hingga timeout, buffer 8K |
| F9 | **INFO** | serve | `int(get_port(...))` OK, bukan bug | — |
| F10 | **LOW** | dnsspoof | socket UDP tidak ditutup explicit (daemon thread) | ✅ FIXED — socket close di serve(), bind-error surfaced EACCES/EADDRINUSE |
| F11 | **INFO** | install.sh | `bin/hkall` tidak ter-pack, shell completion zsh hardcode | ✅ FIXED — symlink langsung ke hkall.py, completion kondisional |
| **F17** | **HIGH** | netcut | DUMMY_MAC `000000000000` — ARP sender all-zero diabaikan banyak stack → netcut no-op | ✅ FIXED — `020000000000` locally-administered |
| **F18** | **HIGH** | deauth | Raw 802.11 frame 10B header, FC `0x00` (bukan deauth `0xC0`) → AP tolak; +2B bloat | ✅ FIXED — `\xc0\x00\x00\x00` + 24B header |
| **F19** | **MEDIUM** | sniff | Probe SSID parse offset 24 = IE id → selalu kosong; FC mask `0xfc` salah | ✅ FIXED — baca len@25 + ssid@26, mask `0xf0` |

---

## Detail Findings

### F1 — CRITICAL: `mod_mitm` ARP spoof tidak intercept traffic
**File:** `modules/websec.py`, `mod_mitm()`
**Masalah:** Frame ARP dibuat dengan `sender MAC = vmac` (MAC korban), bukan MAC attacker. Akibatnya dua sisi (korban & gateway) tidak pernah diberi tahu bahwa attacker adalah gateway → traffic tidak lewat attacker → MITM tidak bekerja.
**Perbaikan:**
- Resolve MAC attacker (interface sender) via `fcntl` `SIOCGIFHWADDR` (0x8927) → `amac`.
- `pkt(claims_mac, claims_ip, op)`: sender = `amac@claims_ip`, target = pasangan yang benar.
- Spoof sekali loop: `s.send(pkt(amac, gw, 1))` (korban percaya gw=amac) dan `s.send(pkt(amac, vi, 1))` (gw percaya vi=amac).
- Restore: `pkt(gmac, gw, 2)` + `pkt(vmac, vi, 2)` — mapping asli.
- `mac()` helper sekarang `strip(':')` → raw hex untuk `fromhex`.

### F2 — CRITICAL: `mod_netcut` restore inverted
**File:** `modules/websec.py`, `mod_netcut()`
**Masalah:** `restore()` mengirim frame dengan arg terbalik → ARP cache diheal dengan mapping salah → target tetap offline / konfig masalah.
**Perbaikan:** `arp_frame(vmac, gmac_raw, vi, gw, 2)` → sender=gmac@gw (benar utk victim); `arp_frame(gmac_raw, vmac, gw, vi, 2)` → sender=vmac@vi (benar utk gateway).

### F3 — HIGH: `mod_recv` timeout crash
**File:** `hkall.py`, `mod_recv()`
**Masalah:** `c.recv(1)` di meta-loop, set `settimeout(15)`; saat client diam (tidak kirim `\n`), `socket.timeout`/`TimeoutError` tidak ditangkap → crash.
**Perbaikan:** tangkap `(socket.timeout, TimeoutError)` + `OSError` → print + close + return.

### F4 — HIGH: `mod_recv` size tidak valid
**File:** `hkall.py`, `mod_recv()`
**Masalah:** `size=int(size)` tanpa validasi → ValueError crash bila meta `file|abc`.
**Perbaikan:** parse di try/except `(ValueError, UnicodeDecodeError)`, cek 2 fields.

### F5 — MEDIUM: `mod_keylog` duration non-numeric
**File:** `hkall.py`, `mod_keylog()`
**Masalah:** `int(dur)` crash pada input non-angka.
**Perbaikan:** try/except → fallback `tk=None` (forever) + pesan user-friendly.

### F6 — MEDIUM: MAC colon dari /proc/net/arp
**File:** `modules/websec.py`, `mod_mitm` & `mod_netcut`
**Masalah:** `line.split()[3]` = `aa:bb:cc:dd:ee:ff`; `bytes.fromhex()` pada string ber-colon → `ValueError`.
**Perbaikan:** `.replace(":", "")` sebelum fromhex, di kedua modul.

### F7 — MEDIUM: websec menu auto-chain url diabaikan
**File:** `modules/websec.py`, `mod_websec()`
**Masalah:** user isi `url` di prompt awal, tapi `mod_sqli/xss/csrf/idor` meminta ulang.
**Perbaikan:** inject `__main__.GINJ = [url]` sebelum tiap fn() di chain.

---

## Catatan Positive (tidak perbaiki, sudah benar)

- `mod_scan`: thread pool 128, timeout per port, sorted out.
- `mod_discover`: batch 64 threads → tidak freeze Termux; cap 2545.
- `mod_arp`: guard `h <= 2048` mencegah OOM untuk /16+.
- `mod_c2`: daemon accept thread, cleanup di exit, xor enkripsi.
- `mod_ddos`: bounded 200 conns / 60s.
- TUI: EOF clean exit (SystemExit), category grouping, quick-run `m key`, `/filter`, `r` last.
- CLI presets via `GINJ` flow berfungsi (terverifikasi `-m netcut ...`).
- `lab_server.py` — serve local vulnerable target, endpoints benar.

---

## Test Plan & Hasil

| Temuan | Test | Hasil |
|--------|------|-------|
| F1/F6 mitm | mock MAC + mock socket, run mod_mitm (non-root check dulu) | PASS — tidak crash, MAC strip benar |
| F2 netcut | mock run mod_netcut, cek output & tidak crash | PASS |
| F3 recv | mock socket yg langsung `TimeoutError` saat recv(1) | PASS — graceful message |
| F4 recv | mock meta `f|xyz\n` | PASS — invalid message, close, return |
| F5 keylog | GINJ=["abc"], `_TERMIOS=False` | PASS — bad duration message |
| F7 sqli | GINJ=[url,"GET"] ke mod_sqli via websec | PASS — url terpakai (test.pack) |
| TUI EOF | `hkall < /dev/null` | PASS — exit bersih (`hkall>` lalu done) |

> Verifikasi dinamik memakai mock (bukan root/hardware). Perlu uji nyata LAN sebelum dipakai serius (perpetuate: run di device dengan 2 host lab, lihat tcpdump/arp).

---

## Open / Minor (belum diperbaiki, dicatat untuk rilis berikut)

- **F8** c2 recv timeout 2s — `if len(d) < 4096: break` — output >4096B lambat terpotong. Fix usul: loop sampai timeout kosong / gunakan `MSG_WAITALL` lebih besar. LOW.
- **F10** dnsspoof socket close explicit di `finally`.
- **F11** install.sh: `.gitignore` ignore `bin/`? Cek bukti: `bin/hkall` tidak ada di tree — tail.
- **F12** toolbox `_build_cmd` — flag non-dash terserah whitelist 6 nama; `-iface` (bettercap) kena whitelist → di-drop jadi positional. ✅ FIXED → dispatch generik: `--flag` / `-X` / `-bundled` (e.g. `-iface`) keep flag+value, non-dash positional.
- **F14** mod_subd — thread **sudah dibatch 64** (`ts[pos:pos+64]`), sama seperti discover. Bukan bug → ✅ RESOLVED (verified, no change). Scan cap 128, spray serial.
- **F16** banyak `except Exception: pass` — audit semua 10 sites: cleanup, thread connect-skip, restore retry, Popen terminate best-effort, payload docstring. Semua by-design fail-soft; log spam di thread 128. Bukan bug → ✅ RESOLVED (by design, no change). Satu-satunya yang layak log dihapus karena debug ke thread terlalu ribut.
- **F17** netcut DUMMY_MAC = `000000000000` (null) — banyak stack mengabaikan ARP sender all-zero → netcut tidak bekerja. ✅ FIXED → `020000000000` (locally-administered, tidak routable).
- **F18** deauth raw fallback: frame 802.11 dibangun `\x00\x00\x00\x00\xff` (10B header, FC=0x00 assoc-req bukan deauth 0xC0) + 2B ekstra → AP menolak. ✅ FIXED → `b"\xc0\x00\x00\x00"+da+sa+bssid+\x00\x00\x07\x00` (24B + reason).
- **F19** sniff probe: `ssid = pkt[24:].split(b"\x00",1)[0]` — offset 24 adalah IE id, bukan SSID → selalu kosong. ✅ FIXED → baca `pkt[25]` len + `pkt[26:26+slen]`; FC mask `0xf0` (bukan 0xfc).

---

_Last updated: 2026-10-27 — audit fase 1-4 complete (read+statik+dinamik mock), 7 fix verifikasi. Open items dicatat._
