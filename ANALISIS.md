# hkall — Analisis Mendalam & Daftar Bug

**Tanggal:** 2026-10-28 (revisi: analisis menyeluruh kedua — selesai baca seluruh sumber)
**Scope:** hkall.py (993L), modules/websec.py (715L), modules/toolbox.py (196L), modules/hello.py, lab/lab_server.py, tools.json, bin/, install.sh, README, docs/MANUAL.md, docs/USAGE.md
**Status:** sesi analisis + perbaikan sebelumnya sudah push 2 commit (`8cf3448`, `4f97693`). Fokus sesi ini = **catat** temuan baru (belum diedit).

---

## Ringkasan Status Fix (yang sudah diperbaiki di sesi sebelumnya)

| # | Sev | Fix | Status |
|---|-----|-----|--------|
| A01 | HIGH | mitm `arf_frame` eksplisit restore arah benar | ✅ |
| A02 | HIGH | netcut src MAC = own MAC, validasi gw | ✅ |
| A09 | MED | csrf parse nilai SameSite Lax/Strict | ✅ |
| A10 | MED | arp sender IP = IP interface asli (UDP trick) | ✅ |
| A11 | MED | deauth validasi MAC regex sebelum fromhex | ✅ |
| A12 | MED | exfil meta `rsplit("|",1)` | ✅ |
| A13 | MED | install.sh zsh case `*/zsh` + guard unset | ✅ |
| A14/A21 | MED/LOW | README count → 34 module, daftar tanpa nomor | ✅ |
| A17 | LOW | eviltwin `p.wait(timeout=2)` anti-zombie + guard port 80 | ✅ |
| A23 | INFO | `--cidr` flag nyata di MODARGS lan/arp | ✅ |
| K1 | MED | AF_PACKET `except (OSError, AttributeError)` semua modul | ✅ |
| (baru) | MED | 6× `int(_ask(...))` → `_ask_int` graceful | ✅ |
| (baru) | MED | `mod_py2exe` `\u0026\u0026` escape literal → `&&` | ✅ |
| A03 | LOW | XOR mapping dc2 sinkron (bukan bug runtime) — butuh handshake (K7) | ⏳ open |
| A18 | LOW | c2 session prune pada OSError sudah ada (`SESSIONS.pop`) | ✅ resolved-nochange |

---

## Temuan Baru (sesi ini — belum diedit)

### N01 — LOW: `compile()`/shell jarang diuji di CI
Tidak ada satupun test; tiap fix sebelumnya diuji manual lewat smoke. `hkall.py` punya `_run` yang mencetak `except Exception` menelan error → bug runtime tersembunyi. **Kemungkinan masa depan:** tambah test smoke script.

### N02 — LOW: `_http_req` timeout 8s pada ddos worker berulang
`mod_ddos` worker loop `while ... and not (...)` dobel kondisi (A07 asli). Tiap worker hingga 200 thread → 200× timeout 8s bisa terkumpul → durasi total membengkak walau `dur<=60`. Tidak fatal (bounded), tapi req/s dipakai report jadi meleset.

### N03 — MED: `cli_one` boolean `--banner` tidak ter-parse di panggilan `cli()`
`build_parser` tidak punya `--banner`; wrapper `hkall -m scan --banner --host X --ports Y` → fase-2 parser pnya `--banner`, jadi OK. Tapi `cli_one` check `if v is True` push "y". Benar. Sedangkan docs MANUAL 1.1 contoh `--banner` tidak dipakai → aman. **Verifikasi:** sudah benar di fase-2. BUKAN bug.

### N04 — MED (potensi): `MODARGS` `--banner` di `scan` tidak ditangani bila tanpa `--ports`
`cli_one`: `if key=="scan" and a.ports: vals.append("n")` — `a.ports` dari fase-1 (parse_known_args). Bila user `-m scan --host X --banner` (tanpa ports), persiapkan `vals += ["1-1000","n"]` → GINJ = [host, "1-1000","n"] tapi `mod_scan` baca urutan host, ports, grab (grab="n"), banner flag di-cli_one tidak masuk GINJ (skip karena bukan di MODARGS dari fase-1? --banner di fase-2 dest banner di extra, bukan a). `cli_one(scan, a, extra)` — a dari fase-1, extra dari fase-2. `--banner` = fase-2, jadi `getattr(extra,'banner')` ada → tapi loop MODARGS skip karena scan punya --banner di MODARGS → loop cek `if flag in (...) continue` — flag `--banner` TIDAK skip (bukan --host/--port/--ports) → `v=extra.banner=True` → `vals.append("y")`. Benar! Lalu scan special-case tidak menimpa GINJ banner krn `if a.ports` false → tambah ["1-1000","n"] SEBELUM "y"?? Urutan: generic push host, ports; lalu per-module push banner "y"; lalu scan special-case `if a.host and not a.ports: vals += ["1-1000","n"]` — ini menimpa! vals = [host, "y", "1-1000", "n"] → GINJ urutan host, y, 1-1000, n → mod_scan baca host✓, ports="y" ✗ salah, grab="1-1000" ✗. **Bug NYATA (low):** `-m scan --host X --banner` (tanpa ports) menghasilkan GINJ cacat. Fix: urutkan banner setelah ports.

### N05 — LOW: `mod_payload` non-obs `HOST,PORT="{host}",{int(port)}` — int port di python-repr, host string; OK. Tapi `xm=True` branch `PORT={port}` string → `int(PORT)` di connect sudah ada. Aman.

### N06 — MED (potensi masa depan): `tools.json` katalog 24 tool tapi `_build_cmd` menangani flag menyatu (`-iface`, `-eval`) dengan menaruh `-iface wlan0` dua argumen — benar untuk getopt. `-T 4` short dengan value: `-T` `4` benar. **Aman.**

### N07 — MED: `mod_idor` POST body dukungan tidak ada
`mod_idor` hanya GET via `_http_req`. Docs §5.4 tidak sebut POST. Aman (scope).

### N08 — MED (masa depan): `lab_server` tidak handle HEAD/OPTIONS — `do_GET`/`do_POST` saja; HTTP 501 untuk HEAD. `enum` GET aman. Minor.

### N09 — LOW: `mod_enum` regex secret mencetak `BEGIN X PRIVATE` tanpa limit — `secrets` bisa besar. Aman.

### N10 — MED: `mod_arp` hasil `found` de-dupe pakai set comprehension `{x for _,x in ...}` setiap iterasi recv — O(n²) untuk /16. Cap 2048 host → masih OK. Minor.

### N11 — LOW: `install.sh` `case "${SHELL:-}"` dengan `;` setelah blok zsh tanpa `;;` kedua — `esac` langsung. Shell valid (single branch). Aman.

### N12 — MED (masa depan): `mod_ops` `subprocess.run(["timeout","5",...])` butuh `timeout` binary — Termux punya. Linux coreutils ada. Risiko jika `timeout` tak terpasang → FileNotFoundError tidak di-catch (hanya di `_tapi`). `mic()`/`vib()`/`cam()` pakai `subprocess.run` langsung tanpa try → traceback. **Potensi bug:** `termux-microphone-record` tak terpasang → FileNotFoundError crash menu ops.

### N13 — LOW: `_ask_int` fallback pesan `(bad number, pakai {default})` bahasa campur — konsisten dgn kode lain.

### N14 — INFO: `mod_sniff` `hits` append tanpa cap (K2 asli sudah dicatat di ANALISIS lama — masih terbuka). **Tetap open.**

### N15 — LOW (masa depan): `_ask` plugin memakai `__main__.GINJ` — kalau module dipanggil di luar hkall (mis. `python -m modules.websec`), `__main__` adalah library → `GINJ` kosong, fallback `input()` baik. Aman.

### N16 — MED: `mod_websec` orchestrator auto-chain set `__main__.GINJ=[url]` → tiap modul baca url, tapi `mod_sqli` prompt `method` kedua — GINJ cuma [url], mod_sqli `_ask("method")` pop habis → EOI → `GINJ` kosong → input() dari stdin. Di tty OK, non-tty EOF→default. **Aman untuk lab.**

### N17 — LOW: `lab_server` `int(i)<=3` tanpa cek negatif — `-1` di path numeric? `i.isdigit()` false utk `-1`, jadi 404. Aman.

### N18 — MED (masa depan): `mod_dnsspoof` `ipb = bytes(int(x) for x in ip.split("."))` — `ip` tak valid (mis. "a.b.c.d") → ValueError crash (tidak di-catch). `_ask` input user. **Potensi bug:** add try.

### N19 — LOW: `mod_eviltwin` `os.chdir(d)` lalu `SimpleHTTPRequestHandler` serving dir `d` — `index.html` ada. Setelah exit, `os.chdir` tidak di-restore → **cwd process hkall berubah** ke temp → file tersimpan ke temp, dan proses lanjut. **Bug nyata (med):** setelah eviltwin selesai, `os.getcwd()` = temp dir; `data/payload.py` dsb di path absolut tetap OK, tapi relatif path user rusak. Fix: restore cwd di finally.

### N20 — LOW: `mod_eviltwin` `_tf.mkdtemp` tidak dibersihkan — temp dir bocor tiap run. Minor leak.

### N21 — MED (masa depan): `scan_ports` `it=iter(ports)` tanpa lock — `next(it)` aman dgn GIL, tidak perlu lock. Benar.

### N22 — LOW: `main_tui` `ids[int(q)-1]` saat `q.isdigit()` tapi filter aktif — index dihitung dari `ids` (filtered). Benar.

---

## Kemungkinan Bug / Risiko Masa Depan

### K1 — AF_PACKET macOS/WSL — ✅ FIXED
### K2 — `mod_sniff` unlimited `hits` (N14) — ✅ FIXED (`HIT_CAP=1000`, probe & creds)
### K3 — `mod_spray` tanpa rate-limit — ✅ FIXED (delay 0.05s/attempt)
### K4 — `_save` sqlite tanpa migration — catatan: schema belum berubah; WAJIB migration bila nanti tambah kolom. Tidak ada kode.
### K5 — config.json korup silent — ✅ FIXED (warning stderr di `load_cfg`)
### K6 — `bin/hkall-deps` sukses palsu — ✅ FIXED (`[FAIL]`/`[ok]` per tool)
### K7 — c2 tanpa auth — ✅ FIXED (PSK handshake `data/c2.psk`; server auth `c2_accept`; payload embed PSK)
### K8 — install.sh non-Termux `pkg` unguarded — ✅ FIXED (`command -v pkg` / apt-get fallback)
### K9 — keylog tty guard — resolved
### K10 — eviltwin cwd — ✅ FIXED
### K11 — ops subprocess guard — ✅ FIXED
### K12 — dnsspoof ipb ValueError — ✅ FIXED
### K13 — cli_one scan banner GINJ order — ✅ FIXED
### K14 — arp dedupe O(n²) — ✅ FIXED (`seen_ips` set O(1))
### N23 — cli_one spray GINJ order cacat (`--users` masuk prompt user_field) — ✅ FIXED (slot khusus spray)
### N24 — recv/serve/c2/exfil bind-in-use & port non-numeric crash — ✅ FIXED (try/except + pesan)
### N25 — parse_ranges trailing comma crash — ✅ FIXED (skip empty part)
### N26 — mod_keylog non-tty termios error — ✅ FIXED (tcgetattr try/except)
### N27 — mod_payload port non-numeric — ✅ FIXED (try int(port) sebelum template)
### N28 — eviltwin temp dir leak — ✅ FIXED (`_tf.rmtree` di finally)

## Sisa open (dok catatan masa depan, tanpa kode)
- K4 sqlite migration — WAJIB migration bila schema `rs` berubah.
- N01 (test otomatis), N02 (ddos timeout bias) — low.

---

## Verifikasi sesi ini
- Baca ulang semua sumber: hkall.py (993L), websec.py (715L), toolbox.py (196L), hello.py, lab_server.py, install.sh, bin/hkall, bin/hkall-deps, tools.json, README/MANUAL/USAGE.
- Commit fix sebelumnya sudah push (`8cf3448`, `4f97693`).
- **Sesi ini difix:** N04 (scan banner order), K10 (eviltwin cwd restore), K11 (ops subprocess guard), K12 (dnsspoof ipb guard).
- **Sesi lanjutan difix:** N23/spray GINJ slot, recv/serve/c2/exfil port guard, keylog non-tty guard, load_cfg warn, parse_ranges comma, spray rate-limit (K3), sniff HIT_CAP (K2), arp seen_ips set (K14), hkall-deps honest FAIL (K6), c2 PSK auth handshake (K7), install.sh pkg guard (K8), eviltwin rmtree (N20). Semua py_compile + shell -n OK.

---
_Dokumen ini hasil analisis statik. Bug kelas network (AF_PACKET, ARP) tetap butuh uji LAN nyata._
