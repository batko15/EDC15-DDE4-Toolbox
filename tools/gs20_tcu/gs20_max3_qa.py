#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unabhaengige End-QA fuer MAX3 FINALE:
   1. MAX2-Superset: jede Werk->MAX2-Aenderung muss identisch in FINAL vorliegen
   2. v2-Schicht: Schluesselwerte verifizieren
   3. .0DA-Struktur: Nicht-Daten-Records byte-identisch zum Werk, Record-Anzahl gleich
   4. Offizieller Checksummen-Pruefer (aus MAX2-Paket) ueber beide .0DA
   5. 512K-Zusammensetzung: Boot FF | Variantendaten==64K | echte App == 0PA
   6. OSS-Finalzustand vs. User-Dump (Werk): nur erwartete Zellen veraendert
"""
import struct, subprocess, sys

D = '/home/z/my-project/download/GS20_MAX3_FINALE'

def load_any(path):
    raw = open(path, 'rb').read()
    if len(raw) == 65536 and b':' not in raw[:200]:
        return bytearray(raw)
    mem = {}; ext = 0
    for line in [l.decode('latin1') for l in raw.splitlines()]:
        if not line.startswith(':'): continue
        cnt = int(line[1:3], 16); addr = int(line[3:7], 16); typ = int(line[7:9], 16)
        if typ == 0:
            a = ext + addr
            for i, by in enumerate(bytes.fromhex(line[9:9 + 2 * cnt])): mem[a + i] = by
        elif typ == 4: ext = int(line[9:13], 16) << 16
        elif typ == 2: ext = int(line[9:13], 16) << 4
    lo = min(a for a in mem if a >= 0x90000)
    img = bytearray([0xFF]) * 0x10000
    for a, b in mem.items():
        if lo <= a < lo + 0x10000: img[a - lo] = b
    return img

W  = load_any('/home/z/my-project/work/stage_final/ext_ORIGINAL_A7563647_BACKUP/ORIGINAL_A7563647_BACKUP.0DA')
M2 = load_any('/home/z/my-project/work/stage_final/ext_GS20_MAX2/GS20_MAX2/GS20_L322_MAX2_20261026-1724_64K.bin')
F  = load_any(f'{D}/GS20_L322_MAX3_FINALE_64K.bin')
FN = load_any(f'{D}/GS20_L322_MAX3_FINALE_64K_OHNE-CRC-LOOP.bin')

fails = []
def chk(cond, msg):
    print(('  [OK] ' if cond else '  [X] ') + msg)
    if not cond: fails.append(msg)

print("== 1) MAX2-Superset ==")
m2_diffs = [(a, struct.unpack_from('<H', M2, a)[0], struct.unpack_from('<H', W, a)[0])
            for a in range(0, 0xFFE0, 2)
            if struct.unpack_from('<H', M2, a)[0] != struct.unpack_from('<H', W, a)[0]]
bad = [(a, m2v, wv) for a, m2v, wv in m2_diffs
       if struct.unpack_from('<H', F, a)[0] != m2v]
chk(len(bad) == 0, f"alle {len(m2_diffs)} MAX2-Diffs in FINAL identisch uebernommen" + (f" - FEHLEN: {bad[:5]}" if bad else ""))

print("== 2) v2-Schicht ==")
for a, v, name in [(0x2472, 5200, 'GlobalAutoup'), (0x2474, 5200, 'GlobalDown'), (0x3094, 5200, 'EGSMax'),
                   (0xC0BC, 32, 'TCC tout2'), (0xC080, 1280, 'TCC diff1'),
                   (0xC05A, 0xA40F, 'TCC mask0'), (0xC05C, 0x002B, 'TCC conf')]:
    chk(struct.unpack_from('<H', F, a)[0] == v, f"0x{a:04X} {name} = {v}")
for a, g in [(0x7736, 'G3min'), (0x76A6, 'G3max')]:
    chk(struct.unpack_from('<H', F, a)[0] == 2816, f"0x{a:04X} Lock {g} = 11.0 km/h")
for a, g in [(0x775A, 'G4min'), (0x76CA, 'G4max')]:
    chk(struct.unpack_from('<H', F, a)[0] == 4608, f"0x{a:04X} Lock {g} = 18.0 km/h")
chk(struct.unpack_from('<H', F, 0x777E)[0] == 8704, "0x777E Lock G5min = 34.0 km/h")

print("== 3) .0DA-Struktur vs. Werk ==")
def recs(path):
    ls = open(path, 'rb').read().split(b'\n')
    return [l.rstrip(b'\r') for l in ls if l.rstrip(b'\r')]
w_recs = recs('/home/z/my-project/work/stage_final/ext_ORIGINAL_A7563647_BACKUP/ORIGINAL_A7563647_BACKUP.0DA')
f_recs = recs(f'{D}/A7563647_MAX3_FINALE.0DA')
chk(len(w_recs) == len(f_recs), f"Record-Anzahl identisch: {len(w_recs)} == {len(f_recs)}")
def is_data(l):
    return l.startswith(b':') and len(l) >= 9 and l[7:9] == b'00'
nd_w = [l for l in w_recs if not is_data(l) and not l.startswith(b'$CHECKSUMME')]
nd_f = [l for l in f_recs if not is_data(l) and not l.startswith(b'$CHECKSUMME')]
chk(nd_w == nd_f, f"alle {len(nd_w)} Nicht-Daten-Records byte-identisch (Typ02/04/01/Text, ohne $CHECKSUMME)")
# $CHECKSUMME-Zeile vorhanden?
cs = [l for l in f_recs if l.startswith(b'$CHECKSUMME')]
chk(len(cs) == 1, f"$CHECKSUMME-Zeile vorhanden: {cs[0].decode() if cs else 'FEHLT'}")

print("== 4) Offizieller Pruefer (MAX2-Werkzeug) ==")
for f in ['A7563647_MAX3_FINALE.0DA', 'A7563647_MAX3_FINALE_OHNE-CRC-LOOP.0DA']:
    r = subprocess.run([sys.executable,
                        '/home/z/my-project/work/stage_final/ext_GS20_MAX2/GS20_MAX2/GS20_CHECKSUMME_pruefen.py',
                        'pruefen', f'{D}/{f}'], capture_output=True, text=True)
    ok = r.returncode == 0 and 'PASS' in r.stdout and r.stdout.count('PASS') == 2
    chk(ok, f"{f}: {r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr}")

print("== 5) 512K-Zusammensetzung ==")
b512 = open(f'{D}/GS20_L322_MAX3_FINALE_512K.bin', 'rb').read()
chk(b512[:0x10000] == b'\xFF' * 0x10000, "Boot-Bereich 0x0-0xFFFF = 0xFF (unberuehrt)")
chk(bytes(b512[0x10000:0x20000]) == bytes(F), "Variantendaten @0x10000 == 64K-Finale")
app512 = b512[0x20000:0x60000]
mem = {}; ext = 0
for line in open('/home/z/my-project/upload/7552700A.0PA', errors='ignore'):
    line = line.strip()
    if not line.startswith(':'): continue
    cnt = int(line[1:3], 16); addr = int(line[3:7], 16); typ = int(line[7:9], 16)
    if typ == 0:
        aa = ext + addr
        for i, by in enumerate(bytes.fromhex(line[9:9 + 2 * cnt])): mem[aa + i] = by
    elif typ == 4: ext = int(line[9:13], 16) << 16
    elif typ == 2: ext = int(line[9:13], 16) << 4
app_ok = all(app512[a - 0xA0000] == b for a, b in mem.items())
chk(app_ok, f"App-Bereich @0x20000 == 7552700A.0PA ({len(mem)} Bytes)")
chk(b512[0x60000:] == b'\xFF' * 0x20000, "Rest 0x60000-0x7FFFF = 0xFF")

print("== 6) OSS-Finalzustand (Werk->FINAL nur in Bloecken 0-6, Spalten 9-16) ==")
OSS, COLS = 0x0564, 18
extra = []
for r in range(104):
    for c in range(18):
        off = OSS + (r * COLS + c) * 2
        if struct.unpack_from('<H', W, off)[0] != struct.unpack_from('<H', F, off)[0]:
            blk, col_ok = r // 8, (9 <= c <= 16)
            row_ok = (r % 8) < 8
            if blk > 6 or not col_ok:
                extra.append((r, c))
chk(len(extra) == 0, "OSS-Aenderungen ausschliesslich Bloecke 0-6, Spalten 9-16" + (f" - UNERWARTET: {extra}" if extra else ""))
n_oss = sum(1 for r in range(104) for c in range(18)
            if struct.unpack_from('<H', W, OSS + (r*COLS+c)*2)[0] != struct.unpack_from('<H', F, OSS + (r*COLS+c)*2)[0])
chk(n_oss == 448, f"OSS: genau 448 Zellen (7 Bloecke x 8 Zeilen x 8 Spalten) veraendert: {n_oss}")
# Kickdown-Spalte 17 unangetastet (Up 1500/2300/3150/5200, Down 0)
c17_ok = all(struct.unpack_from('<H', W, OSS + (r*COLS+17)*2)[0] == struct.unpack_from('<H', F, OSS + (r*COLS+17)*2)[0] for r in range(104))
chk(c17_ok, "OSS Kickdown-Spalte 17 byte-identisch zum Werk")

print()
if fails:
    print(f"QA ERGEBNIS: {len(fails)} FEHLER"); sys.exit(1)
print("QA ERGEBNIS: ALLE PRUEFUNGEN PASS")
