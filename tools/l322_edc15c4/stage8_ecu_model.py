#!/usr/bin/env python3
# 1) Mirror/shadow-copy check  2) ECU-side chain model test (incl. slot words == C)
UP = "/home/z/my-project/upload/"
A  = open(UP+"L322 ORGINAL ECU FUL ALTES STEUERGERATL.bin","rb").read()
K  = open(UP+"WinOLS_Land_Rover_Range_Rover_KENAN_TD6_ORIGINAL_große_Sensoren.bin","rb").read()
M16 = 0xFFFF

def w(d,i): return d[i] | (d[i+1] << 8)

def chain(d, start, end, sa=0, sb=0, fin=True):
    """tdi41v2 chain incl. VAG finalization; returns (a,b) after loop (+final if fin)"""
    p = start
    while True:
        sa = (sa ^ w(d, p)) & M16; p += 2
        n = sb & 0xF
        if n > 0:
            sa = ((sa << n) & M16) | (sa >> (16 - n))
            var2 = sa & 1
        else:
            var2 = 0
        sb = (sb - w(d, p) - var2) & M16; p += 2
        sb = (sb ^ sa) & M16
        if p == end: break
        sa = (sa - w(d, p)) & M16; p += 2
        sa = (sa + 0xDAAC) & M16
        sb = (sb ^ w(d, p)) & M16; p += 2
        n = sa & 0xF
        if n > 0:
            sb = ((sb >> n) | ((sb << (16 - n)) & M16)) & M16
        if p == end: break
    if fin:
        sa = (sa - 0x8631 + 0xDAAC) & M16
        sb = (sb ^ 0xDF9B) & M16
    return sa, sb

print("=== 1) Mirror/shadow check: A[0x0B80+i] vs A[0x70B80+i] for various lengths ===")
for length in (0x5280, 0xB400, 0xB47C, 0x4000, 0x1000, 0x100):
    same = A[0x0B80:0x0B80+length] == A[0x70B80:0x70B80+length]
    nd = sum(1 for x, y in zip(A[0x0B80:0x0B80+length], A[0x70B80:0x70B80+length]) if x != y)
    print(f"  len 0x{length:05X}: identical={same}  differing bytes={nd}")
print("  A[0x0000:0x40] :", A[0x0000:0x40].hex(' '))
print("  A[0x70000:0x7040]:", A[0x70000:0x70040].hex(' '))

print("\n=== 2) ECU-side model: chain over region INCLUDING slot words, from (0,0) ===")
TARGET_A, TARGET_B = 0xB530, 0x4711
tests = [
    ("A [70000,7C000) incl", A, 0x70000, 0x7C000),
    ("K [70000,7C000) incl", K, 0x70000, 0x7C000),
    ("A [70B80,7C000) incl", A, 0x70B80, 0x7C000),
    ("K [70B80,7C000) incl", K, 0x70B80, 0x7C000),
    ("A [14000,70B80) incl", A, 0x14000, 0x70B80),
    ("K [14000,70B80) incl", K, 0x14000, 0x70B80),
]
for label, d, s, e in tests:
    for fin in (False, True):
        for seedtag, (sa0, sb0) in (("(0,0)", (0,0)), ("(8631,EFCD)", (0x8631, 0xEFCD))):
            a, b = chain(d, s, e, sa0, sb0, fin=fin)
            hit = "  <<<HIT" if (a, b) == (TARGET_A, TARGET_B) else ""
            if hit or fin:
                print(f"  {label} fin={int(fin)} {seedtag}: (a,b)=({a:04X},{b:04X}){hit}")

print("\n=== 3) two-call model: [70000,78000) then seed|=(8631,EFCD) then [78000,7C000) ===")
for label, d in (("A", A), ("K", K)):
    a, b = chain(d, 0x70000, 0x78000, 0, 0, fin=False)
    a |= 0x8631; b |= 0xEFCD
    a2, b2 = chain(d, 0x78000, 0x7C000, a, b, fin=False)
    a2f, b2f = chain(d, 0x78000, 0x7C000, a, b, fin=True)
    print(f"  {label}: raw=({a2:04X},{b2:04X}) fin=({a2f:04X},{b2f:04X})"
          + ("  <<<HIT" if (a2, b2) == (TARGET_A, TARGET_B) or (a2f, b2f) == (TARGET_A, TARGET_B) else ""))
