#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GS20 STAGE MAX Patch v2 - L322 TD6 Carbon-Build (700 Nm)
========================================================
Basis: ZB 7563647 (EQ20, E83 X3 3.0d M57D30 MY06) - der im Fahrzeug (L322 TD6,
WinKFP-Flash ZUSB 7563652) aktive Variantendatensatz, verifiziert 2026-10-26.
Alle Stock-Werte wurden aus der echten A7563647.0DA gelesen (nicht aus Foren).

Layout-Wissen (verifiziert):
  - Variandendaten: 64K, HEX-Adressraum 0x90000-0x9FFDF (WinKFP .0DA)
  - Applikation:    256K, HEX-Adressraum 0xA0000-0xDFFDF (WinKFP .0PA)
  - Letzte 32 Bytes je 64K-Segment = vom TCU-Bootloader berechnete CRCs
    (in WinKFP-Dateien 0xFF -> TCU rechnet beim Flashen selbst, kein manueller
     CRC-Fix fuer die WinKFP-Route noetig)
  - Header-Felder CHK1/2/3 @0x0004/0x0008/0x000D: Semantik ungeklaert
    (0x0296 variantenkonstant -> eher Kennung). Stock-Werte wurden vom
    eigenen TCU bereits akzeptiert -> UNVERAENDERT lassen.

Verwendung:
    python3 GS20_MAX_Patch_v2.py <input.0DA oder 64K.bin> [-o outprefix] [--dry]
"""

import sys, struct, argparse
from datetime import datetime

# --- Fahrzeug/Ziel-Konstanten ---------------------------------------------
FDR_NEW      = 4.10     # L322 TD6 Hinterachse 41/10
RPM_TARGET   = 4800     # Volllast-Schaltdrehzahl (M57-Fettabschaltung ~4750-4900)
RPM_MID_FAC  = 0.80     # Faktor fuer 69-81% Spalten
PZU_FAC      = 1.08     # +8% Grunddruck (Carbon vertraegt das, Ventilblock beachten)
GEARS        = [3.419, 2.215, 1.600, 1.000, 0.752]   # aus BIN @0xB060 verifiziert

# OSS-Tabelle
OSS_ADDR, OSS_ROWS, OSS_COLS = 0x0564, 104, 18
OSS_COL_THROTTLE = [0,6,13,19,25,31,38,44,50,56,63,69,75,81,88,94,100,110]
UP_ROWS = {  # Zeilenindex -> (Name, Gangindex)
    8:("E1>2",0),  9:("E2>3",1),  10:("E3>4",2),  11:("E4>5",3),
   16:("S1>2",0), 17:("S2>3",1),  18:("S3>4",2),  19:("S4>5",3),
   24:("XS1>2",0),25:("XS2>3",1), 26:("XS3>4",2), 27:("XS4>5",3),
   32:("A11>2",0),33:("A12>3",1), 34:("A13>4",2), 35:("A14>5",3),
   40:("A21>2",0),41:("A22>3",1), 42:("A23>4",2), 43:("A24>5",3),
   48:("A31>2",0),49:("A32>3",1), 50:("A33>4",2), 51:("A34>5",3),
}

# Skalare: (addr, alt_erwartet_raw, neu_raw, name, einheit, faktor)
SCALARS = [
    (0x7F7E, 27692, 33587, "SYS: Final Drive Ratio *",            "ratio", 8192),
    (0x0290, 27692, 33587, "Final Drive Factor for DTC Check *",  "ratio", 8192),
    (0x2478,   338,   410, "SYS: Speed Param2 / Final Drive Ratio *", "x100", 1),
    (0x2472,  5050,  5200, "LOGIC: Global Autoupshift Threshold", "rpm", 1),
    (0x2474,  5050,  5200, "LOGIC: Global Downshift Threshold",   "rpm", 1),
    (0x3094,  5000,  5200, "SYS: EGS Maximum RPM Limit",          "rpm", 1),
    (0xC122,  4000,  5600, "TCC: Max Torque to switch STAT6 ON",  "Nm", 8),
    (0xC120,  4000,  5600, "TCC: Max Torque to switch STAT7 ON",  "Nm", 8),
    (0xC0C2,   640,   320, "TCC: Timeout to switch STAT6 ON, AC Corr.", "ms", 1),
    (0xC0BE,   640,   320, "TCC: Timeout to switch STAT7 ON",     "ms", 1),
    (0xC0BC,    64,    32, "TCC: Timeout2 to switch STAT6 ON",    "ms", 1),
    (0xC080,   960,  1280, "TCC: Motor-Turbine diff to switch STAT7 ON", "rpm", 8),
    (0xC082,   640,   960, "TCC: Motor-Turbine diff2 to switch STAT7 ON", "rpm", 8),
]
BITFIELDS = [
    (0xC05A, 0xA60B, 0xA40F, "TCC: Bitmask 0 (TCC bleibt bei Upshifts zu) [Forum]"),
    (0xC05C, 0x00AF, 0x002B, "TCC: STAT0-6-7-8 CONF (Lock-During-Shift) [Forum]"),
]

# Lock-Speed-Tabellen (kmh, /256): (addr, gear, stockflat, newflat)
LOCK_SPEEDS = [
    (0x7712, 2, 7.0,  7.0),   # G2 MIN -> unveraendert
    (0x7682, 2, 7.0,  7.0),   # G2 MAX -> unveraendert
    (0x7736, 3, 12.5, 11.0),
    (0x76A6, 3, 12.5, 11.0),
    (0x775A, 4, 21.0, 18.0),
    (0x76CA, 4, 21.0, 18.0),
    (0x777E, 5, None, 34.0),  # G5: Stock variert 37-39.3 (Spalten 0-14), Kickdown-Spalten bleiben
    (0x76EE, 5, None, 34.0),
]

# Adaptive-Druck-Deckel (Adoption der Parallel-Session-Idee: Carbon darf bis 11 bar adaptieren)
ADAPT_PRESSURE = [
    (0x330E, 9936, 11000, "PRESSURE: Max Downshift Adaptation Pressure", 1000),
    (0x6C54, 9936, 11000, "PRESSURE: Max Upshift Adaptation Pressure",   1000),
]

PZU_ADDR, PZU_ROWS, PZU_COLS = 0x62C2, 2, 11
CRC_CFG_ADDR, CRC_CFG_BIT = 0x31C0, 0x08
APP_0PA = "/home/z/my-project/work/gd20/GD20_7552700/data/GD20/7552700A.0PA"

LOG=[]
def log(m=""):
    print(m); LOG.append(m)

def rd16(b,a): return struct.unpack_from("<H",b,a)[0]
def wr16(b,a,v): struct.pack_into("<H",b,a,v & 0xFFFF)

def load(path):
    """.0DA (HEX) oder rohes 64K-BIN laden -> (data, srclines|None, hexbase)"""
    raw=open(path,'rb').read()
    has_hex = any(l.startswith(b':') for l in raw.splitlines()[:200])
    if has_hex:
        lines=[l.decode('latin1') for l in raw.splitlines()]
        mem={}; ext=0
        for line in lines:
            if not line.startswith(':'): continue
            cnt=int(line[1:3],16); addr=int(line[3:7],16); typ=int(line[7:9],16)
            if typ==0:
                a=ext+addr
                for i,by in enumerate(bytes.fromhex(line[9:9+2*cnt])): mem[a+i]=by
            elif typ==4: ext=int(line[9:13],16)<<16
            elif typ==2: ext=int(line[9:13],16)<<4
        lo=min(a for a in mem if a>=0x90000)   # Basis = Variantendaten-Sektion
        img=bytearray([0xFF])*(0x10000)
        for a,b in mem.items():
            if lo<=a<lo+0x10000: img[a-lo]=b
        return img, lines, lo
    return bytearray(raw), None, 0

def save_0DA(outpath, srclines, base, data):
    """Line-Replay: ALLE Originalzeilen erhalten (typ-02/04/16/01, Text),
    nur die Daten-Payloads der typ-00-Records werden ersetzt, Record-Checksummen neu."""
    out=[]; ext=0; n=0
    for line in srclines:
        if not line.startswith(':'):
            out.append(line); continue
        cnt=int(line[1:3],16); addr=int(line[3:7],16); typ=int(line[7:9],16)
        if typ==2: ext=int(line[9:13],16)<<4
        elif typ==4: ext=int(line[9:13],16)<<16
        if typ!=0:
            out.append(line); continue
        a=ext+addr
        off=a-base
        if 0<=off<len(data):
            chunk=bytes(data[off:off+cnt])
            rec=f":{cnt:02X}{addr:04X}00{chunk.hex().upper()}"
            s=(cnt+((addr>>8)&0xFF)+(addr&0xFF)+0+sum(chunk))&0xFF
            rec+=f"{((-s)&0xFF):02X}"
            out.append(rec); n+=1
        else:
            out.append(line)   # ausserhalb (sollte nicht vorkommen) - Original erhalten
    open(outpath,'w',newline='\n').write("\n".join(out)+"\n")
    return n

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o","--outprefix", default=None)
    ap.add_argument("--dry", action="store_true")
    a=ap.parse_args()

    log("="*76)
    log(f"GS20 STAGE MAX PATCH v2 - L322 TD6 Carbon-Build 700Nm (Basis 7563647/EQ20)")
    log(f"{datetime.now():%Y-%m-%d %H:%M:%S}  |  Eingabe: {a.input}")
    log("="*76)

    data, srclines, hexbase = load(a.input)
    if len(data) not in (0xFFE0, 0x10000):
        log(f"[X] Unerwartete Groesse {len(data)} - Abbruch"); sys.exit(2)
    if len(data)==0xFFE0:
        # auf 64K auffüllen (Ende = TCU-CRC-Bereich)
        data = data + bytearray([0xFF])*(0x10000-len(data))
        log("[i] 0xFFE0-Bild erkannt (.0DA) - auf 64K aufgefuellt")
    if rd16(data,0x3FD8)!=0x3633 and data[0x3FD8:0x3FDF]!=b'7563647':
        log("[!] WARNUNG: SW-NR-Feld ist nicht '7563647' - Basis pruefen!")
    log(f"[i] SW-NR: {bytes(data[0x3FD8:0x3FDF]).decode('latin1',errors='replace')}")
    log(f"[i] CHK1/2/3 (unveraendert): 0x{struct.unpack_from('<I',data,4)[0]:08X} / "
        f"0x{rd16(data,8):04X} / 0x{rd16(data,0xD):04X}")

    n_changes=0

    log("\n[1] Fahrzeug-Anpassung L322 (Achse 4.10 statt E83 3.38)")
    for addr,old,new,name,unit,fac in SCALARS[:3]:
        cur=rd16(data,addr)
        ok = "OK" if cur==old else "ABWEICHUNG!"
        log(f"    0x{addr:04X} {name:44s} {cur/fac:8.3f} -> {new/fac:6.3f} [{ok}]")
        if not a.dry: wr16(data,addr,new)
        n_changes+=1

    log("\n[2] Drehzahl-Headroom (Diesel abregelt eh bei ~4800)")
    for addr,old,new,name,unit,fac in SCALARS[3:6]:
        cur=rd16(data,addr)
        ok = "OK" if cur==old else "ABWEICHUNG!"
        log(f"    0x{addr:04X} {name:44s} {cur:8d} -> {new:6d} [{ok}]")
        if not a.dry: wr16(data,addr,new)
        n_changes+=1

    log("\n[3] TCC - Wandlerchluss fuer Carbon-Build 700 Nm")
    for addr,old,new,name,unit,fac in SCALARS[6:]:
        cur=rd16(data,addr)
        ok = "OK" if cur==old else "ABWEICHUNG!"
        log(f"    0x{addr:04X} {name:44s} {cur/fac:8.1f} -> {new/fac:6.1f} {unit} [{ok}]")
        if not a.dry: wr16(data,addr,new)
        n_changes+=1
    for addr,old,new,name in BITFIELDS:
        cur=rd16(data,addr)
        ok = "OK" if cur==old else "ABWEICHUNG!"
        log(f"    0x{addr:04X} {name:44s} 0x{cur:04X} -> 0x{new:04X} [{ok}]")
        if not a.dry: wr16(data,addr,new)
        n_changes+=1

    log("    Lock-Speeds (Auto, kmh) - frueherer Wandlerchluss im Reiseprogramm:")
    for addr,g,old,new in LOCK_SPEEDS:
        if old==new:
            log(f"      G{g} @0x{addr:04X}: {new:.1f} kmh (unveraendert)")
            continue
        cur0=rd16(data,addr)/256.0
        if not a.dry:
            for c in range(15):              # Spalten 0-14; Kickdown (15,16) bleibt
                wr16(data,addr+c*2,int(round(new*256)))
        n_changes+=15
        log(f"      G{g} @0x{addr:04X}: {cur0:.1f} -> {new:.1f} kmh (Spalten 0-14, Kickdown bleibt)")

    log(f"\n[4] PRESSURE: Base Pressure P_ZU @0x{PZU_ADDR:04X} (2x11) x{PZU_FAC:.2f}")
    if not a.dry:
        for r in range(PZU_ROWS):
            for c in range(PZU_COLS):
                ad=PZU_ADDR+(r*PZU_COLS+c)*2
                old=rd16(data,ad); new=min(0xFFFF,round(old*PZU_FAC))
                wr16(data,ad,new); n_changes+=1
            old0=rd16(data,PZU_ADDR+r*PZU_COLS*2)
            log(f"    Reihe {r+1} erste Zelle: {old0/1000:.2f} -> {min(0xFFFF,round(old0*PZU_FAC))/1000:.2f} bar")
    log(f"[4b] Adaptive-Druck-Deckel 9,94 -> 11,0 bar (Carbon darf adaptieren)")
    for addr,old,new,name,fac in ADAPT_PRESSURE:
        cur=rd16(data,addr)
        ok = "OK" if cur==old else "ABWEICHUNG!"
        log(f"    0x{addr:04X} {name:44s} {cur/fac:6.2f} -> {new/fac:5.2f} bar [{ok}]")
        if not a.dry: wr16(data,addr,new)
        n_changes+=1

    log(f"\n[5] OSS-Schaltpunkte @0x{OSS_ADDR:04X}: Volllast auf {RPM_TARGET} rpm (Programme E/S/XS/A1-A3)")
    if not a.dry:
        ch=0
        for r,(name,gi) in sorted(UP_ROWS.items()):
            t_full=round(RPM_TARGET/GEARS[gi])
            t_mid =round(RPM_TARGET*RPM_MID_FAC/GEARS[gi])
            for c in range(11,17):           # 69/75/81% = mid, 88-100% = full
                ad=OSS_ADDR+(r*OSS_COLS+c)*2
                old=rd16(data,ad)
                tgt = t_full if c>=14 else t_mid
                if old<tgt:
                    wr16(data,ad,tgt); ch+=1
                    if c in (11,14):
                        log(f"    {name:6s} {OSS_COL_THROTTLE[c]:3d}%: {old:5d} -> {tgt:5d} OSS")
            ad=OSS_ADDR+(r*OSS_COLS+17)*2    # 110% Kickdown: nur anheben
            old=rd16(data,ad)
            if old<t_full:
                wr16(data,ad,t_full); ch+=1
                log(f"    {name:6s} 110%: {old:5d} -> {t_full:5d} OSS (Kickdown)")
        n_changes+=ch
        log(f"    => {ch} OSS-Zellen angepasst (nur Anhebungen, Teillast <63% unberuehrt)")

    log(f"\n[6] Unveraendert (bewusst):")
    log("    - CHK1/2/3 Header (Stock, vom TCU akzeptiert)")
    log("    - CRC CONFIG @0x31C0 (Bit3 bleibt AN - TCU rechnet Segment-CRCs selbst)")
    log("    - EGS High Temp 140C / Hyst 130C (Schutz bleibt!)")
    log("    - Downshift-OSS-Tabellen, Shifttime-Offsets (Stufe 2, optional)")

    if a.dry:
        log("\n[DRY-RUN] nichts geaendert."); sys.exit(0)

    pre=a.outprefix or "GS20_7563647_MAX_L322"
    open(pre+"_64K.bin","wb").write(bytes(data[:0x10000]))
    log(f"\n[OK] {pre}_64K.bin  (64K Kalibrierung fuer TunerPro/Flash-Tool)")

    # Variante OHNE CRC-LOOP (Notnagel: Bit3 in CRC CONFIG @0x31C0 geloescht)
    d2=bytearray(data)
    oldcrc=d2[CRC_CFG_ADDR]
    d2[CRC_CFG_ADDR]=oldcrc & ~CRC_CFG_BIT & 0xFF
    open(pre+"_64K_OHNE-CRC-LOOP.bin","wb").write(bytes(d2[:0x10000]))
    log(f"[OK] {pre}_64K_OHNE-CRC-LOOP.bin  (Fallback: CRC CONFIG 0x{oldcrc:02X} -> 0x{d2[CRC_CFG_ADDR]:02X})")

    # 512K-Gesamtbild: Boot=FF (NIEMALS voll beschreiben!) | Variantendaten | echte App aus 0PA
    img512=bytearray([0xFF])*0x80000
    img512[0x10000:0x20000]=data
    try:
        app = bytearray([0xFF])*0x40000
        mem={}; ext=0
        for line in open(APP_0PA, errors='ignore'):
            line=line.strip()
            if not line.startswith(':'): continue
            cnt=int(line[1:3],16); addr=int(line[3:7],16); typ=int(line[7:9],16)
            if typ==0:
                aa=ext+addr
                for i,b in enumerate(bytes.fromhex(line[9:9+2*cnt])): mem[aa+i]=b
            elif typ==4: ext=int(line[9:13],16)<<16
            elif typ==2: ext=int(line[9:13],16)<<4
        base=0xA0000
        for a2,b in mem.items():
            if base<=a2<base+0x40000: app[a2-base]=b
        img512[0x20000:0x60000]=app
        log(f"[OK] 512K: echte App aus 7552700A.0PA eingebettet ({len(mem)} Bytes)")
    except Exception as e:
        log(f"[!] App nicht eingebettet ({e}) - 512K nur mit Datenfenster")
    open(pre+"_512K.bin","wb").write(bytes(img512))
    log(f"[OK] {pre}_512K.bin  (Boot 0x0-0xFFFF = FF! Nur partiell flashen oder WinKFP-Route!)")

    if srclines:
        n=save_0DA(pre+".0DA", srclines, hexbase, data)
        log(f"[OK] {pre}.0DA  (WinKFP-kompatibel via Line-Replay, {n} Records neu geschrieben)")

    open(pre+"_log.txt","w",encoding="utf-8").write("\n".join(LOG))
    log(f"[OK] {pre}_log.txt")
    log(f"\n==> {n_changes} Werte veraendert.")
    log("""
NÄCHSTE SCHRITTE (WinKFP-Route, wie beim letzten Mal):
  1. Original A7563647.0DA im SP-Datenordner (data/GD20) SICHERN
  2. Diese .0DA als A7563647.0DA in den Ordner legen (Name behalten!)
  3. WinKFP -> Komfortmodus -> SG ADCD/GD20 -> ZUSB 7563652 -> Programmieren
  4. Nach Flash: 1 Minute Zündung an, NICHT starten; dann Adaptionen reset
     (INPA: GS20 -> F6 Activate -> F3 Reset Adaptionen) ODER 30 km Lernfahrt
  5. Fehlerspeicher prüfen, Schaltverhalten testen
""")
    log("RUECKWEG: Original-A7563647.0DA zurueckkopieren -> gleicher WinKFP-Flash.")

if __name__=="__main__":
    main()
