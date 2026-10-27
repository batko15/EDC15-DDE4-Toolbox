#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task 8 / Schritt 12: BUILD - Map-Transplantat 330D(1037351761) -> RR(1037351777).
Strategie:
  - Basis = cal_rr (WinOLS 'grosse Sensoren', SW 1037351777)
  - Kopiere saemtliche Differenz-Regionen aus t761 (330D 1600BAR-Tune),
    shift-korrigiert (Insertion 2 Woerter bei 0x03862, danach donor = rr_off - 4)
  - GESCHUETT (bleibt RR): Header/Verzeichnis, sig-Felder, grosse-Sensoren-Record,
    DTC-Konfig-Zonen (Spender hat Abschaltungen), EGR-Verdachtszone, SW-Nummer,
    strukturelle Insertion, unbekannte 90da-Zone
  - EWS/Codierung/Code-Bereich: unberuehrt (nur Cal-Block 0x70000-0x7C000 wird angefasst)
"""
import os, struct, json, hashlib

WORK = '/home/z/my-project/work/L322_TD6_merge'
OUT = '/home/z/my-project/download/L322_TD6_DDE4_Transplant'
os.makedirs(OUT, exist_ok=True)

def load(k): return open(os.path.join(WORK, k + '.bin'), 'rb').read()
l322, rr = load('l322_orig'), load('rr_winols')
t777, t761 = load('tune_777'), load('tune_761')
cal_rr = rr[0x70000:0x7C000]

# --- Diff-Regionen rr vs 761 (aus Script 03, regionliste konsistent neu berechnet) ---
def diff_regions(a, b, block=16):
    regs, cur = [], None
    for gi in range(len(a) // block):
        off = gi * block
        if a[off:off+block] != b[off:off+block]:
            if cur and cur[1] == off: cur[1] = off + block
            else:
                if cur: regs.append(tuple(cur))
                cur = [off, off + block]
    if cur: regs.append(tuple(cur))
    return regs

src761_for_rr = lambda off: (off - 4) if off >= 0x3866 else off
regs = diff_regions(cal_rr, bytes(t761[src761_for_rr(o)] if False else t761[src761_for_rr(o)]
                                  for o in range(0)))  # Platzhalter

# Eigentlich: vergleiche cal_rr gegen shift-korrigierten Spender
donor_aligned = bytearray(cal_rr)
for o in range(len(cal_rr)):
    donor_aligned[o] = t761[src761_for_rr(o)]
regs = diff_regions(cal_rr, bytes(donor_aligned))
print(f'Diff-Regionen (rr vs shift-korrigierter 761): {len(regs)}')

# --- Schutzliste (KEEP) ---
KEEP = [
    (0x00000, 0x00010),  # Container-Header/Feld 0x0008
    (0x00B70, 0x00B80),  # Signatur 1 (97c1-Feld)
    (0x01820, 0x01845),  # 'grosse Sensoren'-Record (9ada-Daten)
    (0x01850, 0x01860),  # Drucklimit-Record (rr==761, no-op, der Vollstaendigkeit halber)
    (0x018D0, 0x01930),  # 90da-Zone (versions-spezifisch, Struktur differiert)
    (0x01E80, 0x01EC0),  # DTC/Monitor-Konfig (Spender: deaktiviert)
    (0x02010, 0x02030),  # DTC/Monitor-Konfig
    (0x02520, 0x02550),  # DTC/Monitor-Konfig
    (0x028C0, 0x02900),  # DTC-Schwellen (Spender: ffff-Muster)
    (0x033E0, 0x03400),  # DTC-Schwellen
    (0x0BFB0, 0x0BFC0),  # SW-Nummer 1037351777
    (0x0BFF0, 0x0C000),  # Signatur 2 (97c1-Feld)
]
INSERT_KEEP = (0x03862, 0x03866)  # 2 strukturelle Extra-Woerter der RR-Version

def in_keep(off):
    return any(s <= off < e for s, e in KEEP)

merged = bytearray(cal_rr)
copied_regions, kept_regions = [], []
for (s, e) in regs:
    if in_keep(s) and in_keep(e - 1):
        kept_regions.append((s, e))
        continue
    changed = 0
    for off in range(s, e):
        if in_keep(off):
            continue
        if INSERT_KEEP[0] <= off < INSERT_KEEP[1]:
            continue
        src = src761_for_rr(off)
        if merged[off] != t761[src]:
            merged[off] = t761[src]
            changed += 1
    copied_regions.append({'start': s, 'end': e, 'bytes_changed': changed})

n_changed = sum(r['bytes_changed'] for r in copied_regions)
print(f'Kopierte Regionen: {len(copied_regions)}, geaenderte Bytes: {n_changed}')
print(f'Geschuetzte Regionen: {len(kept_regions)}')

# --- Einbetten in Full-Flash ---
full = bytearray(rr)
full[0x70000:0x7C000] = merged

# --- Dateien schreiben ---
p_full = os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_FULL_512K.bin')
p_cal  = os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_CAL_48K.bin')
open(p_full, 'wb').write(full)
open(p_cal, 'wb').write(bytes(merged))

md5 = lambda b: hashlib.md5(b).hexdigest()
print(f'\nFULL 512K: {p_full}')
print(f'  MD5 {md5(full)}')
print(f'CAL 48K : {p_cal}')
print(f'  MD5 {md5(merged)}')

# --- JSON fuer QA/Protokoll ---
json.dump({
    'copied': copied_regions,
    'kept': [list(k) for k in kept_regions],
    'keep_list': [list(k) for k in KEEP],
    'insert_keep': list(INSERT_KEEP),
    'md5_full': md5(full), 'md5_cal': md5(merged),
    'bytes_changed': n_changed,
}, open(os.path.join(WORK, 'build_report.json'), 'w'), indent=1)
print('\nbuild_report.json geschrieben.')
