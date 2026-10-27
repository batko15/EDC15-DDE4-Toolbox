#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task 8 / Schritt 13: QA - 3-Wege-Verifikation des Transplantats."""
import os, struct, json

WORK = '/home/z/my-project/work/L322_TD6_merge'
OUT = '/home/z/my-project/download/L322_TD6_DDE4_Transplant'
def load(k): return open(os.path.join(WORK, k + '.bin'), 'rb').read()
l322, rr = load('l322_orig'), load('rr_winols')
t777, t761 = load('tune_777'), load('tune_761')

merged_full = open(os.path.join(OUT, 'L322_TD6_1037351777_330D1600BAR_Transplant_FULL_512K.bin'), 'rb').read()
merged = merged_full[0x70000:0x7C000]
cal_rr = rr[0x70000:0x7C000]

SHIFT_AT = 0x3866
def src(off): return off - 4 if off >= SHIFT_AT else off

report = []
ok_all = True

def check(name, cond, detail=''):
    global ok_all
    status = 'PASS' if cond else 'FAIL'
    if not cond: ok_all = False
    report.append((status, name, detail))
    print(f'  [{status}] {name} {detail}')

print('=== QA 1: Full-Flash-Integritaet ===')
check('Bereich 0x00000-0x70000 byte-identisch mit rr_winols (Code/EWS/Fahrzeugdaten unberuehrt)',
      merged_full[:0x70000] == rr[:0x70000])
check('Bereich 0x7C000-0x80000 byte-identisch mit rr_winols',
      merged_full[0x7C000:] == rr[0x7C000:])

print('=== QA 2: merged vs rr (nur Kopier-Regionen geaendert) ===')
build = json.load(open(os.path.join(WORK, 'build_report.json')))
copied = [(c['start'], c['end']) for c in build['copied']]
expected_bytes = build['bytes_changed']
diff_offs = [i for i in range(0xC000) if merged[i] != cal_rr[i]]
in_copied = [i for i in diff_offs if any(s <= i < e for s, e in copied)]
check(f'Anzahl geaenderter Bytes = {expected_bytes} (laut Build)', len(diff_offs) == expected_bytes,
      f'(ist {len(diff_offs)})')
check('Alle Aenderungen liegen in kopierten Regionen', len(in_copied) == len(diff_offs))
# Kopierte Regionen muessen VOLLSTAENDIG geaendert haben (wo donor != rr)
missing = []
for (s, e) in copied:
    for off in range(s, e):
        if off in range(*build['insert_keep']) or any(a <= off < b for a, b in build['keep_list']):
            continue
        if t761[src(off)] != cal_rr[off] and merged[off] != t761[src(off)]:
            missing.append(off)
check('Keine ausgelassenen Spender-Bytes in Kopier-Regionen', not missing, f'{missing[:10]}')

print('=== QA 3: merged vs 761 (nur Schutz-Zonen + Insertion differieren) ===')
keep = [tuple(k) for k in build['keep_list']] + [tuple(build['insert_keep'])]
residual = []
for i in range(0xC000):
    if merged[i] != t761[src(i)]:
        if not any(s <= i < e for s, e in keep):
            residual.append(i)
check('Rest-Differenzen zum Spender ausschliesslich in Schutz-Zonen', not residual,
      f'{[hex(x) for x in residual[:12]]}')

print('=== QA 4: Semantische Stichproben ===')
def w(d, o, n): return struct.unpack_from(f'<{n}H', d, o)[0] if n == 1 else struct.unpack_from(f'<{n}H', d, o)
# 1) Drucklimit-Record bedb: rr/761 = 18000 muss erhalten bleiben
check('Rail-Druck-Limit (bedb-Record) = 18000', w(merged, 0x1856, 1) == 18000, f'ist {w(merged, 0x1856, 1)}')
# 2) grosse-Sensoren-Record 9ada: rr-Werte [188,500,3000,3313]
check('Sensor-Record 9ada = rr-Werte', list(w(merged, 0x182C, 4)) == [188, 500, 3000, 3313],
      f'ist {list(w(merged, 0x182C, 4))}')
# 3) SW-Nummer im Cal bleibt 1037351777
check('SW-Nummer im Cal = 1037351777', merged[0xBFB0:0xBFBA] == b'1037351777')
# 4) Sechs Karten: Kern-Daten jetzt = Spender
for idx, (s_rr, s_76) in enumerate([(0x5C30, 0x5C2C), (0x6056, 0x6052), (0x647C, 0x6478),
                                    (0x68A2, 0x689E), (0x6CC8, 0x6CC4), (0x70EE, 0x70EA)]):
    a = merged[s_rr + 48:s_rr + 72]
    b = t761[s_76 + 48:s_76 + 72]
    check(f'Karte{idx+1} Daten = Spender', a == b)
# 5) IQ-Achse = Spender (bis 1510)
check('IQ-Achse @0xA1C4 = Spender-Achse', merged[0xA1C4:0xA1C4+30] == t761[0xA1C0:0xA1C0+30])
# 6) DTC-Liste unveraendert (war identisch, muss es bleiben)
check('DTC-Liste 0xB210-0xB6A0 unveraendert', merged[0xB210:0xB6A0] == cal_rr[0xB210:0xB6A0])
# 7) Signaturen unveraendert
check('sig1 @0x0B7C = rr', merged[0x0B7C:0x0B80] == cal_rr[0x0B7C:0x0B80])
check('sig2 @0xBFFC = rr', merged[0xBFFC:0xC000] == cal_rr[0xBFFC:0xC000])
# 8) Header-Feld 0x0008 = rr
check('Header-Feld 0x0008 = rr', merged[0x0008:0x000C] == cal_rr[0x0008:0x000C])
# 9) Insertion-Woerter = rr
check('Struktur-Insertion 0x3862 = rr', merged[0x3862:0x3866] == cal_rr[0x3862:0x3866])

print('=== QA 5: Vorher/Nachher-Kennwerte (Spender-Werte jetzt aktiv) ===')
rows = []
# b80b/1027-Zone (0x380C-0x3826): rr hatte 3000, Spender 10000
rows.append(('Limit-Feld 0x380C (9 Woerter)', list(w(cal_rr, 0x380C, 4)), list(w(merged, 0x380C, 4))))
# 56c1-Kurve @0x3898: Daten
rows.append(('Kurve 56c1 @0x3898 Data', list(w(cal_rr, 0x38A4, 6)), list(w(merged, 0x38A4, 6))))
for name, before, after in rows:
    print(f'   {name}: {before} -> {after}')

json.dump({'ok': ok_all, 'report': report}, open(os.path.join(WORK, 'qa_report.json'), 'w'), indent=1)
print(f'\nGESAMT: {"ALLE PASS" if ok_all else "FEHLER VORHANDEN"}')
