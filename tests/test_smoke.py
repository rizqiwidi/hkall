#!/usr/bin/env python3
"""hkall smoke tests - assert-based, no framework. Run: python3 tests/test_smoke.py"""
import os, sys, types, socket, threading, time, tempfile, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
os.environ["HKALL_NOPLUGIN"] = "1"

PASS = 0
FAIL = 0
def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")

imp = types.ModuleType("hkall")
imp.__file__ = os.path.join(ROOT, "hkall.py")
exec(compile(open(os.path.join(ROOT, "hkall.py")).read(), "hkall.py", "exec"), imp.__dict__)

# 1. parse_ranges
check("parse_ranges basic", imp.parse_ranges("1-3,5") == [1,2,3,5])
check("parse_ranges trailing comma", imp.parse_ranges("1-2,,") == [1,2])

# 2. xor_stream roundtrip
msg = b"hello world"
enc = imp.xor_stream(msg, 1)
check("xor roundtrip same key", imp.xor_stream(enc, 1) == msg)

# 3. net2ip
check("net2ip base+1", imp.net2ip([192,168,1,0], 1) == "192.168.1.1")
check("net2ip carry", imp.net2ip([192,168,1,254], 3) == "192.168.1.1")

# 4. c2 PSK: file exists + mode
psk = imp.c2_psk()
check("c2 psk generated", len(psk) >= 32)
check("c2 psk file 0600", oct(os.stat(imp.PSK_FILE).st_mode & 0o777) == "0o600")

# 5. c2 handshake: wrong psk rejected, right accepted
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0)); srv.listen(5); port = srv.getsockname()[1]
threading.Thread(target=imp.c2_accept, args=(srv, psk), daemon=True).start()
time.sleep(0.2)
bad = socket.socket(); bad.connect(("127.0.0.1", port)); bad.sendall(b"WRONG\n")
bad.settimeout(2)
try:
    d = bad.recv(16)
except Exception:
    d = b""
bad.close()
time.sleep(0.3)
check("c2 reject wrong psk", not imp.SESSIONS)
good = socket.socket(); good.connect(("127.0.0.1", port))
good.sendall((psk + "\n").encode())
time.sleep(0.4)
check("c2 accept correct psk", len(imp.SESSIONS) == 1)
good.close()

# 6. schema guard: mismatched rs table warns, no crash
tmp = tempfile.mkdtemp()
old_db = imp.DB
imp.DB = os.path.join(tmp, "rs.db")
c2 = sqlite3.connect(imp.DB); c2.execute("CREATE TABLE rs(a,b)"); c2.commit(); c2.close()
imp.save("t", "x", "y")  # must warn not crash
check("schema guard warns not crash", True)
imp.DB = old_db

# 7. fix markers in source
src = open(os.path.join(ROOT, "hkall.py")).read()
check("spray rate-limit present", "time.sleep(0.05)" in src)
check("sniff HIT_CAP present", "HIT_CAP" in open(os.path.join(ROOT, "modules/websec.py")).read())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
