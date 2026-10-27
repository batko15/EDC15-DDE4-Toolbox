#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task 8 / Schritt 1: Inventur der 4 DDE4-BINs (Groesse, MD5, Strings, Identifikation)."""
import os, hashlib, shutil, re, json

UP = '/home/z/my-project/upload'
WORK = '/home/z/my-project/work/L322_TD6_merge'
os.makedirs(WORK, exist_ok=True)

SRCS = {
    'l322_orig': 'L322 ORGINAL ECU FUL ALTES STEUERGERATL.bin',
    'rr_winols': 'WinOLS_Land_Rover_Range_Rover_KENAN_TD6_ORIGINAL_große_Sensoren.bin',
    'tune_777':  'Unknown_DDE4_1037351777_tune.bin',
    'tune_761':  '1600 BAR TUNQn_DDE4_1037351761_tune.bin',
}

def entropy(data):
    if not data: return 0.0
    from collections import Counter
    import math
    c = Counter(data)
    n = len(data)
    return -sum((v/n) * math.log2(v/n) for v in c.values())

info = {}
for key, fn in SRCS.items():
    p = os.path.join(UP, fn)
    data = open(p, 'rb').read()
    dst = os.path.join(WORK, key + '.bin')
    shutil.copyfile(p, dst)

    # ASCII-Strings >= 5 Zeichen
    strs = [s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{5,}', data)]
    interesting = [s for s in strs if re.search(r'\d{3,}', s)]
    # UTF-16LE-Strings (manche Tools schreiben so)
    u16 = re.findall((rb'(?:[\x20-\x7e]\x00){5,}'), data)
    u16s = [s.decode('utf-16-le') for s in u16][:20]

    # Entropie-Karriere über 8KB-Blöcke (Kartenbereiche = mäßige Entropie, Code = hoch)
    blocks = []
    for off in range(0, len(data), 0x8000):
        e = entropy(data[off:off+0x8000])
        blocks.append(round(e, 2))

    info[key] = {
        'orig_name': fn,
        'size': len(data),
        'size_hex': hex(len(data)),
        'md5': hashlib.md5(data).hexdigest(),
        'strings_with_digits': interesting[:60],
        'utf16_strings': u16s,
        'entropy_per_32K': blocks,
    }
    # ersten/letzten 64 Bytes als Hex
    info[key]['head_64'] = data[:64].hex()
    info[key]['tail_64'] = data[-64:].hex()

with open(os.path.join(WORK, 'inventory.json'), 'w', encoding='utf-8') as f:
    json.dump(info, f, indent=1, ensure_ascii=False)

for k, v in info.items():
    print('='*100)
    print(f"[{k}]  size={v['size']} ({v['size_hex']})  md5={v['md5']}")
    print(f"  head64: {v['head_64']}")
    print(f"  tail64: {v['tail_64']}")
    print(f"  entropy/32K: {v['entropy_per_32K']}")
    print(f"  strings w/ digits ({len(v['strings_with_digits'])} shown <=60):")
    for s in v['strings_with_digits'][:40]:
        print(f"    {s[:120]}")
    if v['utf16_strings']:
        print(f"  utf16: {v['utf16_strings'][:10]}")
print('\nSaved ->', os.path.join(WORK, 'inventory.json'))
