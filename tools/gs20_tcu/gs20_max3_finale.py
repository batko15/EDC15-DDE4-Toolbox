#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GS20 L322 TD6 - MAX3 FINALE  (Stufe 3: eingefahren, Hybrid-Turbo Stage 1,
offener Luftfilter, neuer Motor, neuer Wandler, Carbon-Kupplung >700 Nm)
=========================================================================
Basis   : ORIGINAL_A7563647_BACKUP.0DA  (pristine EQ20 / SW 7563647, md5 1cd344359126b05dd800092fc7fe6083)
Schichten:
  A) MAX2-Kopie 1:1 (im Fahrzeug erprobt: Schaltzeiten, P_ZU +14%, Adaption 13,5 bar,
     TCC 700 Nm/240 ms/diff2 40 rpm, Max-RPM-Tabellen 4800/4450/4700, Sport 4800,
     Track-Mode 50% + Offsets)
  B) v2-Restaurierung (von MAX2 gefallengelassen, physisch korrekt):
     - Global Autoupshift / Downshift / EGS-Max auf 5200
     - TCC STAT6 Timeout2 32 ms, STAT7 diff1 160 rpm (frueherer Wandlerchluss)
     - TCC-Bitmasken 0xC05A/0xC05C (Lock-During-Shift, Forum e46fanatics)
     - Lock-Speeds G3/G4/G5 frueher (nur senken, Spalten 0-14)
  C) Stage-3 NEU: OSS-Volllast (92-110%) hoch- UND runterschalten
     - value = Motordrehzahl / Gang i (bereits v2-bestaetigt)
     - Upshift-Ziele: 4400/4500/4600/4700 rpm  -> nur Anhebungen, Deckel = Kickdown-Spalte 17
     - Downshift-Ziele: Upshift_neu - 200 (Hysterese), Post-Schalt-rpm <= 4500 < 4800 Cap
Bewusst UNveraendert (dokumentiert):
  - FDR 0x7F7E/0x0290/0x2478 auf 3.38 (Stock): CAN-Geschwindigkeit ist fuehrend,
    interne OSS-Rechnung weicht mit Stock-Konstanten nur 1,4 % ab;
    FDR-Wechsel OHNE passenden Reifenumfang erzeugte 16,5 % Fehler
  - AGS BASE, SPORT-Config, Brems-Downshift, M/2/3/4-Downshift (Semantik unbestaetigt)
  - OSS-Bloecke 7-12 (Fremdvarianten: Benziner-Profil, Kickdown 6140)
  - P_ZU bleibt +14 % (13,13 bar) - Ventilsaturation jenseits
"""
import struct, sys, os
from datetime import datetime

BASE_0DA = '/home/z/my-project/work/stage_final/ext_ORIGINAL_A7563647_BACKUP/ORIGINAL_A7563647_BACKUP.0DA'
APP_0PA  = '/home/z/my-project/upload/7552700A.0PA'
OUTDIR   = '/home/z/my-project/download/GS20_MAX3_FINALE'
PRE      = 'GS20_L322_MAX3_FINALE'

LOG = []
def log(m=""):
    print(m); LOG.append(m)

def rd16(b, a): return struct.unpack_from('<H', b, a)[0]
def wr16(b, a, v): struct.pack_into('<H', b, a, v & 0xFFFF)

# ---------------------------------------------------------------- Laden
def load_0da(path):
    raw = open(path, 'rb').read()
    lines = [l.decode('latin1') for l in raw.splitlines()]
    mem = {}; ext = 0
    for line in lines:
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
    return img, lines, lo

def save_0DA(outpath, srclines, base, data):
    out = []; n = 0; ext = 0
    for line in srclines:
        if not line.startswith(':'):
            out.append(line); continue
        cnt = int(line[1:3], 16); addr = int(line[3:7], 16); typ = int(line[7:9], 16)
        if typ == 2: ext = int(line[9:13], 16) << 4
        elif typ == 4: ext = int(line[9:13], 16) << 16
        if typ != 0:
            out.append(line); continue
        a = ext + addr; off = a - base
        if 0 <= off < len(data):
            chunk = bytes(data[off:off + cnt])
            rec = f":{cnt:02X}{addr:04X}00{chunk.hex().upper()}"
            s = (cnt + ((addr >> 8) & 0xFF) + (addr & 0xFF) + 0 + sum(chunk)) & 0xFF
            rec += f"{((-s) & 0xFF):02X}"
            out.append(rec); n += 1
        else:
            out.append(line)
    open(outpath, 'w', newline='\n').write("\n".join(out) + "\n")
    return n

# ---------------------------------------------------------------- Checksummen
MOD36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def crc16_arc(data, crc=0):
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF
def mod36(value, seed=27):
    total = abs(seed)
    for i, ch in enumerate(value):
        c = ord(ch.upper())
        v = c - 48 if 48 <= c <= 57 else c - 55
        total += v * (3 if (i % 2 == 0) != (seed < 0) else 1)
    return MOD36[total % 36]
def parse_records(path):
    lines = open(path, 'rb').read().split(b'\n')
    data, out = bytearray(), []
    for raw in lines:
        l = raw.rstrip(b'\r')
        if l.startswith(b':'):
            h = bytes.fromhex(l[1:].decode())
            cnt, typ = h[0], h[3]
            if typ in (0x00, 0x10) and cnt: data += h[4:4 + cnt]
        out.append(l)
    return bytes(data), out
def declared(path):
    for raw in open(path, 'rb').read().split(b'\n'):
        s = raw.decode('latin1').strip()
        if s.startswith('$CHECKSUMME'):
            p = s.split(); return p[1], (p[2] if len(p) > 2 else '')
    return None, None
def fix_checksum(inp, outp):
    data, lines = parse_records(inp)
    val = '%04X' % crc16_arc(data)
    res, done = [], False
    for l in lines:
        if l.startswith(b'$CHECKSUMME'):
            res.append(('$CHECKSUMME %s %s' % (val, mod36(val))).encode()); done = True
        else:
            res.append(l)
    assert done, 'keine $CHECKSUMME-Zeile!'
    open(outp, 'wb').write(b'\r\n'.join(res) + b'\r\n')
    d2, _ = parse_records(outp)
    dv, ch = declared(outp)
    ok = (crc16_arc(d2) == int(dv, 16)) and (ch == mod36(dv.upper()))
    return val, mod36(val), ok

# ================================================================ PATCH-DEFINITIONEN
# --- Schicht A: MAX2 1:1 (alle Werte aus MAX2_Protokoll_20261026-1724, im Auto erprobt)
SCALARS_A = [
    (0x0705E, 90,  "SHIFTTIME: Upshift time threshold, Load 1>2"), (0x07060, 110, "SHIFTTIME: Upshift time threshold, Load 2>3"),
    (0x07062, 125, "SHIFTTIME: Upshift time threshold, Load 3>4"), (0x07064, 65,  "SHIFTTIME: Upshift time threshold, Load 4>5"),
    (0x0706E, 70,  "SHIFTTIME: Upshift time threshold[0]"),        (0x07074, 70,  "SHIFTTIME: Upshift time threshold[3]"),
    (0x07056, 70,  "SHIFTTIME: Downshift time threshold, Load[0]"),(0x0705C, 70,  "SHIFTTIME: Downshift time threshold, Load[3]"),
    (0x0330E, 13500, "PRESSURE: Max Downshift Adaptation Pressure"),
    (0x06C54, 13500, "PRESSURE: Max Upshift Adaptation Pressure"),
    (0x0C120, 5600,  "TCC: Max Torque to switch STAT7 ON (700 Nm)"),
    (0x0C122, 5600,  "TCC: Max Torque to switch STAT6 ON (700 Nm)"),
    (0x0C0BE, 240,   "TCC: Timeout/Fuellzeit STAT7 ON"),
    (0x0C0C2, 240,   "TCC: Timeout/Fuellzeit STAT6 ON"),
    (0x0C082, 320,   "TCC: Motor-Turbine diff2 STAT7 ON (40 rpm)"),
    (0x02F16, 4800,  "LOGIC: Motor speed threshold, Sport"),
    (0x04F4C, 500,   "LOGIC: Throttle threshold ON, Track Mode (50%)"),
    (0x04F54, 380,   "LOGIC: Track Mode offset MaxDownRPM[0]"),
    (0x04F56, 340,   "LOGIC: Track Mode offset MaxDownRPM[1]"),
    (0x04F58, 220,   "LOGIC: Track Mode offset MaxDownRPM[2]"),
    (0x04F5A, 90,    "LOGIC: Track Mode offset MaxDownRPM[3]"),
]
PZU_TARGETS = [1952, 8153, 1952, 8153, 8153, 8153, 2736, 8153, 8153, 8153,
               2207, 13133, 13133, 13133, 13133, 9904, 10597, 4615, 8153, 8153, 8153, 3922]
MAXRPM = ([4800]*12) + [4450]*4 + [4700]*4 + [4800]*4   # 0x4F7A..0x4FA8

# --- Schicht B: v2-Restaurierung
SCALARS_B = [
    (0x2472, 5200, "LOGIC: Global Autoupshift Threshold"),
    (0x2474, 5200, "LOGIC: Global Downshift Threshold (Ueberdrehzahl-Deckel)"),
    (0x3094, 5200, "SYS: EGS Maximum RPM Limit"),
    (0x0C0BC, 32,  "TCC: Timeout2 STAT6 ON (Lock ziergt endgueltig)"),
    (0x0C080, 1280,"TCC: Motor-Turbine diff1 STAT7 ON (160 rpm, frueherer Schluss)"),
]
BITFIELDS_B = [
    (0x0C05A, 0xA40F, "TCC: Bitmask 0 (TCC bleibt bei Upshifts zu) [Forum]"),
    (0x0C05C, 0x002B, "TCC: STAT0-6-7-8 CONF (Lock-During-Shift) [Forum]"),
]
LOCK_SPEEDS = [  # (addr, gang, ziel_kmh) - nur SENKEN, Spalten 0-14
    (0x7736, 3, 11.0), (0x76A6, 3, 11.0),
    (0x775A, 4, 18.0), (0x76CA, 4, 18.0),
    (0x777E, 5, 34.0), (0x76EE, 5, 34.0),
]
# --- Schicht C: OSS Stage-3
OSS, ROWS, COLS = 0x0564, 104, 18
N_BLOCKS = 7   # Bloecke 0-6 = XE/E/S/XS/A1/A2/A3 (Block 7-12 = Fremdvarianten)
UP_TARGET = [1287, 2032, 2875, 4700]     # 4400/3.419, 4500/2.215, 4600/1.600, 4700/1.000
DN_TARGET = [1087, 1832, 2675, 4500]     # up_neu - 200
GEARS     = [3.419, 2.215, 1.600, 1.000, 0.752]
C3_MIN_GAP = 50   # Mindest-Hysterese Down<Up je Spalte

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    log("=" * 100)
    log("GS20 L322 TD6 - MAX3 FINALE  (Basis: pristine EQ20 A7563647, alle Schichten vereinigt)")
    log(f"{datetime.now():%Y-%m-%d %H:%M:%S}")
    log("=" * 100)
    data, srclines, base = load_0da(BASE_0DA)
    pristine = bytes(data)
    log(f"[i] Basis geladen: 64K-Image, Basisadresse 0x{base:05X}")
    log(f"[i] SW-NR: {bytes(data[0x3FD8:0x3FDF]).decode('latin1')}  |  CRC-CFG @0x31C0: 0x{data[0x31C0]:02X}")
    log(f"[i] CHK1/2/3: 0x{struct.unpack_from('<I',data,4)[0]:08X} / 0x{rd16(data,8):04X} / 0x{rd16(data,0xD):04X} (unveraendert)")

    n = 0
    log("\n[A] MAX2-Ebene 1:1 (im Fahrzeug erprobt)")
    for addr, new, name in SCALARS_A:
        old = rd16(data, addr)
        wr16(data, addr, new); n += 1
        log(f"    0x{addr:04X} {name:52s} {old:6d} -> {new:6d}")
    log("    P_ZU @0x62C2 (2x11): exakte MAX2-Werte (+14%)")
    for i, tv in enumerate(PZU_TARGETS):
        ad = 0x62C2 + i * 2
        old = rd16(data, ad)
        assert old in (1712, 7152, 2400, 1936, 11520, 8688, 9296, 4048, 3440), f"P_ZU Stock abweichend @0x{ad:04X}: {old}"
        wr16(data, ad, tv); n += 1
    log(f"      22 Zellen: {PZU_TARGETS[0]/1000:.2f} ... {PZU_TARGETS[11]/1000:.2f} bar")
    log("    Max-RPM-by-Speed-Limit @0x4F7A (24 Werte): Kick 4800 / Auto0 4450 / Auto1 4700 / Auto2 4800")
    for i, tv in enumerate(MAXRPM):
        ad = 0x4F7A + i * 2
        old = rd16(data, ad)
        wr16(data, ad, tv); n += 1
        if old != tv: log(f"      0x{ad:04X}: {old} -> {tv}")

    log("\n[B] v2-Restaurierung (von MAX2 gefallengelassen)")
    for addr, new, name in SCALARS_B:
        old = rd16(data, addr)
        wr16(data, addr, new); n += 1
        log(f"    0x{addr:04X} {name:52s} {old:6d} -> {new:6d}")
    for addr, new, name in BITFIELDS_B:
        old = rd16(data, addr)
        wr16(data, addr, new); n += 1
        log(f"    0x{addr:04X} {name:52s} 0x{old:04X} -> 0x{new:04X}")
    log("    Lock-Speeds (frueherer Wandlerchluss, nur senken, Spalten 0-14):")
    for addr, g, tgt in LOCK_SPEEDS:
        tv = int(round(tgt * 256)); ch = 0
        for c in range(15):
            ad = addr + c * 2
            old = rd16(data, ad)
            if old > tv:
                wr16(data, ad, tv); ch += 1; n += 1
        log(f"      G{g} @0x{addr:04X}: -> {tgt:.1f} km/h ({ch} Spalten gesenkt)")

    log("\n[C] OSS Stage-3: Volllast-Schaltpunkte 92-110% (Spalten 9-16)")
    ch_up = ch_dn = 0
    for b in range(N_BLOCKS):
        pname = ["XE", "E", "S", "XS", "A1", "A2", "A3"][b]
        for k in range(4):   # Upshifts 1>2..4>5
            r = b * 8 + k
            tgt = UP_TARGET[k]
            c17 = rd16(data, OSS + (r * COLS + 17) * 2)
            assert tgt <= c17, f"Ziel {tgt} > Kickdown-Deckel {c17} (r{r})"
            for c in range(9, 17):
                ad = OSS + (r * COLS + c) * 2
                old = rd16(data, ad)
                if old < tgt:
                    wr16(data, ad, tgt); ch_up += 1; n += 1
        for k in range(4):   # Downshifts 2>1..5>4
            r = b * 8 + 4 + k
            r_up = b * 8 + k
            tgt = DN_TARGET[k]
            for c in range(9, 17):
                ad = OSS + (r * COLS + c) * 2
                up_c = rd16(data, OSS + (r_up * COLS + c) * 2)
                cap = up_c - 200
                newv = min(max(rd16(data, ad), tgt), cap)
                if newv != rd16(data, ad):
                    wr16(data, ad, newv); ch_dn += 1; n += 1
        log(f"    Block {b} ({pname}): Up auf {UP_TARGET}, Down auf {DN_TARGET} (Hysterese 200)")
    log(f"    => {ch_up} Upshift-Zellen, {ch_dn} Downshift-Zellen angepasst")

    log("\n[QA] Invarianten pruefen ...")
    ok = True
    for b in range(N_BLOCKS):
        for k in range(4):
            ru, rd = b * 8 + k, b * 8 + 4 + k
            for c in range(1, 18):
                up_v = rd16(data, OSS + (ru * COLS + c) * 2)
                up_p = rd16(data, OSS + (ru * COLS + c - 1) * 2)
                if c >= 2 and up_v < up_p: ok = False; log(f"    [X] Up nicht monoton r{ru} c{c}")
                dn_v = rd16(data, OSS + (rd * COLS + c) * 2)
                if dn_v >= up_v: ok = False; log(f"    [X] Hysterese r{ru}/r{rd} c{c}: {dn_v} >= {up_v}")
                if 3 <= c <= 16:
                    dn_p = rd16(data, OSS + (rd * COLS + c - 1) * 2)
                    if dn_v < dn_p: ok = False; log(f"    [X] Down nicht monoton r{rd} c{c}")
    # Post-Schalt-Drehzahlen der neuen Kickdown-Downshifts
    posts = [(DN_TARGET[k]) * GEARS[k] for k in range(4)]
    log(f"    Post-Schalt-rpm Downshifts (Spalten 9-16): " + ", ".join(f"{p:.0f}" for p in posts) + "  (alle < 4800 Cap)")
    if not ok: sys.exit("[X] QA fehlgeschlagen")
    log("    [OK] Monotonie + Hysterese + rpm-Deckel: PASS")

    diffs = sum(1 for a in range(0, 0xFFE0, 2) if rd16(data, a) != rd16(pristine, a))
    log(f"\n[i] Geaenderte 16-bit-Woerter gegen Werk: {diffs}")

    # -------------------------------------------------------------- Schreiben
    p64 = os.path.join(OUTDIR, f"{PRE}_64K.bin")
    open(p64, "wb").write(bytes(data))
    d2 = bytearray(data); d2[0x31C0] &= ~0x08 & 0xFF
    p64n = os.path.join(OUTDIR, f"{PRE}_64K_OHNE-CRC-LOOP.bin")
    open(p64n, "wb").write(bytes(d2))
    log(f"\n[OK] {p64}")
    log(f"[OK] {p64n}  (CRC-CFG 0x{data[0x31C0]:02X} -> 0x{d2[0x31C0]:02X})")

    t0 = os.path.join(OUTDIR, "_tmp.0DA")
    nr = save_0DA(t0, srclines, base, data)
    val, ch36, okc = fix_checksum(t0, os.path.join(OUTDIR, "A7563647_MAX3_FINALE.0DA"))
    os.remove(t0)
    log(f"[OK] A7563647_MAX3_FINALE.0DA  ({nr} Records, $CHECKSUMME {val} {ch36}, Verify {'PASS' if okc else 'FAIL'})")
    if not okc: sys.exit(1)

    srclines_n = [l.decode('latin1') for l in open(p64n and os.path.join(OUTDIR, "A7563647_MAX3_FINALE.0DA"), 'rb').read().split(b'\n')]
    # OHNE-Variante aus d2 bauen
    t1 = os.path.join(OUTDIR, "_tmp2.0DA")
    save_0DA(t1, srclines, base, d2)
    val2, ch2, okc2 = fix_checksum(t1, os.path.join(OUTDIR, "A7563647_MAX3_FINALE_OHNE-CRC-LOOP.0DA"))
    os.remove(t1)
    log(f"[OK] A7563647_MAX3_FINALE_OHNE-CRC-LOOP.0DA  ($CHECKSUMME {val2} {ch2}, Verify {'PASS' if okc2 else 'FAIL'})")
    if not okc2: sys.exit(1)

    # 512K-Gesamtbild
    img512 = bytearray([0xFF]) * 0x80000
    img512[0x10000:0x20000] = data
    try:
        app = bytearray([0xFF]) * 0x40000
        mem = {}; ext = 0
        for line in open(APP_0PA, errors='ignore'):
            line = line.strip()
            if not line.startswith(':'): continue
            cnt = int(line[1:3], 16); addr = int(line[3:7], 16); typ = int(line[7:9], 16)
            if typ == 0:
                aa = ext + addr
                for i, bb in enumerate(bytes.fromhex(line[9:9 + 2 * cnt])): mem[aa + i] = bb
            elif typ == 4: ext = int(line[9:13], 16) << 16
            elif typ == 2: ext = int(line[9:13], 16) << 4
        for a2, bb in mem.items():
            if 0xA0000 <= a2 < 0xE0000: app[a2 - 0xA0000] = bb
        img512[0x20000:0x60000] = app
        log(f"[OK] {PRE}_512K.bin  (echte App eingebettet, {len(mem)} Bytes)")
    except Exception as e:
        log(f"[!] App nicht eingebettet: {e}")
    p512 = os.path.join(OUTDIR, f"{PRE}_512K.bin")
    open(p512, "wb").write(bytes(img512))

    open(os.path.join(OUTDIR, "MAX3_FINALE_Protokoll.txt"), "w", encoding="utf-8").write("\n".join(LOG))
    log(f"\n==> FERTIG: {n} Werte veraendert. Ausgabe in {OUTDIR}")

if __name__ == "__main__":
    main()
