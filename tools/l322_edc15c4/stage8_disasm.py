#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/z/my-project/work/refs/edc15-tools")
from c166_dis import dis

UP = "/home/z/my-project/upload/"
A = open(UP+"L322 ORGINAL ECU FUL ALTES STEUERGERATL.bin","rb").read()

RANGES = [
    ("slot1/slot2 check flow", 0x113A0, 0x11440),
    ("check flow 1 (0x11046)", 0x10FF0, 0x11070),
    ("check flow 2 (0x112EA)", 0x11280, 0x11300),
    ("background monitor",     0x11A40, 0x11B60),
]
for name, s, e in RANGES:
    print(f"================ {name} (file 0x{s:05X}-0x{e:05X}, CPU 0x{0x80000+s:05X}) ================")
    for line in dis(A, 0x80000, s, e):
        print(line)
    print()
