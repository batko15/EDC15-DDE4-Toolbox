#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task 8 / Schritt 6: Record-Parser fuer den DDE4-Cal-Container (48K).
Modell: <marker 2B> <count 2B LE> <axis count x u16> <data count x u16> (Werte LE).
Testet verschiedene Framings und laeuft blockweise durch."""
import os, struct, json

WORK = '/home/z/my-project/work/L322_TD6_merge'
def load(k): return open(os.path.join(WORK, k + '.bin'), 'rb').read()
l322, rr = load('l322_orig'), load('rr_winols')
t777, t761 = load('tune_777'), load('tune_761')
cal = {'l322': l322[0x70000:0x7C000], 'rr': rr[0x70000:0x7C000], 't777': t777, 't761': t761}

BLOCK_END = 0xBC00   # danach Identifier/Bereich

def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]

def parse(d, start, end):
    """Versucht Record-Kette zu laufen. Gibt (records, next_off, fail_at) zurueck."""
    recs = []
    off = start
    while off + 4 <= end:
        marker = struct.unpack_from('<H', d, off)[0]
        cnt = u16(d, off + 2)
        if cnt == 0 or cnt > 0x0400:
            return recs, off, f'count={cnt} @0x{off:04X}'
        need = 4 + cnt * 4
        if off + need > end:
            return recs, off, f'ueberlaeuft @0x{off:04X}'
        axis = [u16(d, off + 4 + 2*i) for i in range(cnt)]
        data = [u16(d, off + 4 + 2*cnt + 2*i) for i in range(cnt)]
        recs.append({'off': off, 'marker': f'{marker:04X}', 'cnt': cnt,
                     'axis': axis, 'data': data, 'size': need})
        off += need
    return recs, off, None

# Startpunkt: erster bekannter Record fac1 @0x38B4? Nein -- von 0 suchen:
# Wir probieren Starts an allen 4-Byte-Grenzen und bewerten Abdeckung.
best = None
for start in range(0x0010, 0x0200, 2):
    recs, nxt, fail = parse(cal['rr'], start, BLOCK_END)
    cov = sum(r['size'] for r in recs)
    if best is None or cov > best[0]:
        best = (cov, start, len(recs), nxt, fail)
print(f'Bester Start: 0x{best[1]:04X}: {best[2]} Records, Abdeckung {best[0]} B '
      f'({100*best[0]/(BLOCK_END-best[1]):.1f} %), Ende 0x{best[3]:04X}, Fail: {best[4]}')

# Wo scheitert es konkret? Parse ab bestem Start und drucke die ersten Fehler-Umgebungen
cov, start, n, nxt, fail = best
recs, nxt, fail = parse(cal['rr'], start, BLOCK_END)
print(f'\nErster Fail-Punkt: {fail}')
if fail:
    fo = int(fail.split('@')[1].rstrip(']').strip()[2:-1], 16) if '@0x' in fail else None
# Umgebung um den Failpunkt hexdump-en
if '@0x' in str(fail):
    fo = int(fail.split('@0x')[1], 16)
    print(f'Hexdump cal_rr um 0x{fo:04X}:')
    for i in range(max(start, fo-32), min(BLOCK_END, fo+64), 16):
        print(f'   {i:04X}: {cal["rr"][i:i+16].hex()}')

# Recordliste (rr) speichern und kompakt ausgeben
out = []
for r in recs:
    out.append(r)
json.dump(out, open(os.path.join(WORK, 'records_rr.json'), 'w'), indent=1)

print(f'\nRecord-Tabelle rr ({len(recs)} Records, bis 0x{nxt:04X}):')
print('  Off    Mark  Cnt  Axis(F~)                     Data(F~)')
for r in recs[:80]:
    ax = ','.join(str(x) for x in r['axis'][:6]) + ('...' if r['cnt'] > 6 else '')
    da = ','.join(str(x) for x in r['data'][:6]) + ('...' if r['cnt'] > 6 else '')
    print(f'  0x{r["off"]:04X} {r["marker"]} {r["cnt"]:4d}  [{ax}]  [{da}]')
if len(recs) > 80:
    print(f'  ... {len(recs)-80} weitere (siehe records_rr.json)')
