#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task 8 / Schritt 14: Variante B (Spender-DTC-Abschaltung fuer HFM-Test) + DTC-Analyse."""
import os, struct, hashlib, json

WORK = '/home/z/my-project/work/L322_TD6_merge'
OUT = '/home/z/my-project/download/L322_TD6_DDE4_Transplant'
def load(k): return open(os.path.join(WORK, k + '.bin'), 'rb').read()
rr = load('rr_winols')
t761 = load('tune_761')
t777 = load('tune_777')

calA = open(os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_CAL_48K.bin'), 'rb').read()
fullA = open(os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_FULL_512K.bin'), 'rb').read()

# --- DTC-Listen-Analyse ---
def be_words(d, a, b):
    out = []
    for i in range(a, b, 2):
        out.append(struct.unpack_from('>H', d, i)[0])
    return out

# Wo genau steht die DTC-Liste? 0xB210+: 0x0Exx/0x0Fxx-Codes
dtc_zone = calA[0xB210:0xB6A0]
codes = be_words(dtc_zone, 0, len(dtc_zone))
dtc_like = [c for c in codes if 0x0E00 <= c <= 0x0FFF or 0x2800 <= c <= 0x28FF or c == 0]
print(f'DTC-Liste 0xB210-0xB6A0: {len(codes)} Woerter, davon 0x0Exx/0x0Fxx: '
      f'{sum(1 for c in codes if 0x0E00 <= c <= 0x0FFF)}')
print(f'  0x0F8E in Liste? {0x0F8E in codes}   0x2805? {0x2805 in codes}   0x2802? {0x2802 in codes}')
# Vorkommen von 0x0F8E als LE/BE irgendwo vor 0xB210
cnt = 0
for i in range(0x0010, 0xB210, 2):
    v = struct.unpack_from('<H', calA, i)[0]
    if v == 0x0F8E:
        cnt += 1
print(f'  0x0F8E als LE-Wort vor 0xB210: {cnt}x')

# --- Variante B bauen ---
calB = bytearray(calA)
# Schutz-/DTC-Zonen des Spenders uebernehmen (alle < 0x3866 -> aligned, kein Shift)
B_ZONES = [(0x028C0, 0x02900), (0x033E0, 0x03400)]
changed = 0
for s, e in B_ZONES:
    for i in range(s, e):
        if calB[i] != t761[i]:
            calB[i] = t761[i]
            changed += 1
print(f'\nVariante B: {changed} Bytes aus DTC-Abschaltzonen des Spenders uebernommen')

fullB = bytearray(fullA)
fullB[0x70000:0x7C000] = calB

pB_cal = os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_VARIANTE-B_HFM-DTC_CAL_48K.bin')
pB_full = os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_VARIANTE-B_HFM-DTC_FULL_512K.bin')
open(pB_cal, 'wb').write(bytes(calB))
open(pB_full, 'wb').write(bytes(fullB))
md5 = lambda b: hashlib.md5(b).hexdigest()
print(f'  {pB_cal}\n    MD5 {md5(calB)}')
print(f'  {pB_full}\n    MD5 {md5(fullB)}')

# --- Verifikation Variante B ---
diffB = [(i, calA[i], calB[i]) for i in range(0xC000) if calA[i] != calB[i]]
assert all(any(s <= i < e for s, e in B_ZONES) for i, _, _ in diffB), 'B-Aenderung ausserhalb Zonen!'
assert bytes(calB[0x28C0:0x2900]) == t761[0x28C0:0x2900]
assert bytes(calB[0x33E0:0x03400]) == t761[0x33E0:0x03400]
print(f'  Verifikation: {len(diffB)} Bytes differieren zu Variante A, alle in B-Zonen, Inhalt == Spender  [PASS]')

# --- Doku der B-Zonen-Inhalte (fuer Protokoll) ---
print('\nB-Zone 1 (0x28C0-0x2900) rr/777 vs Spender:')
print('  rr  :', calA[0x28C0:0x2900][:48].hex())
print('  761 :', t761[0x28C0:0x2900][:48].hex())
print('B-Zone 2 (0x33E0-0x3400) rr/777 vs Spender:')
print('  rr  :', calA[0x33E0:0x3400][:48].hex())
print('  761 :', t761[0x33E0:0x3400][:48].hex())

json.dump({'B_zones': B_ZONES, 'B_bytes': changed,
           'md5_calB': md5(calB), 'md5_fullB': md5(fullB)},
          open(os.path.join(WORK, 'build_report_B.json'), 'w'), indent=1)
print('\nbuild_report_B.json geschrieben.')
