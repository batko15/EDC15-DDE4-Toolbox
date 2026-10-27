#!/usr/bin/env python3
"""GS20 / NFS Checksummen-Werkzeug  (Siemens GS20, GA10C, WinKFP/INPA/NCS)

Berechnet, prueft und schreibt $CHECKSUMME in BMW-.0DA/.0PA/.krw-Dateien.

Algorithmus (zweifach bewiesen):
  CRC-16/ARC  -  Poly 0x8005, reflektiert (=0xA001), init 0x0000, kein Final-XOR
  Datenbasis  -  concatenate DATA-Felder aller Intel-HEX-Records mit Typ 00 und
                 Typ 10, in Datei-Reihenfolge
  Pruefzeichen- Mod36-Check-Character, Seed 27, ueber den 4 Hex-Ziffern
Beweise:  A7563647.0DA -> F999 (deklariert F999)
          7552700A.0PA -> CFFA (deklariert CFFA)
          "$CHECKSUMME DEADBEEF" -> Mod36-Char 'B'  (der BMW-Platzhalter)
          $CARB_MODE_9_CVN 00004E74 -> 'J'

Aufruf:
  python3 GS20_CHECKSUMME.py pruefen DATEI[.0DA/.0PA]
  python3 GS20_CHECKSUMME.py berichtigen EINGABE.0DA AUSGABE.0DA
"""
import sys

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


def parse(path):
    lines = open(path, 'rb').read().split(b'\n')
    data, out = bytearray(), []
    for raw in lines:
        l = raw.rstrip(b'\r')
        if l.startswith(b':'):
            h = bytes.fromhex(l[1:].decode())
            cnt, typ, d = h[0], h[3], h[4:4 + h[0]]
            if typ in (0x00, 0x10) and cnt:
                data += d
        out.append(l)
    return bytes(data), out


def declared(path):
    for raw in open(path, 'rb').read().split(b'\n'):
        s = raw.decode('latin1').strip()
        if s.startswith('$CHECKSUMME'):
            p = s.split()
            return p[1], (p[2] if len(p) > 2 else '')
    return None, None


def check(path):
    data, _ = parse(path)
    calc = crc16_arc(data)
    decl, ch = declared(path)
    if decl is None:
        print('%s: KEIN $CHECKSUMME gefunden (%d Datenbytes)' % (path, len(data)))
        return False
    okv = calc == int(decl, 16)
    okc = ch == mod36(decl.upper())
    print('%s' % path)
    print('  Datenbytes      : %d (0x%X)' % (len(data), len(data)))
    print('  deklariert      : $CHECKSUMME %s %s' % (decl, ch))
    print('  gerechnet       :   %04X %s' % (calc, mod36('%04X' % calc)))
    print('  Wert            : %s' % ('PASS' if okv else 'FAIL  -> die Datei wurde veraendert, ohne die Checksumme zu erneuern'))
    print('  Mod36-Zeichen   : %s' % ('PASS' if okc else 'FAIL'))
    return okv and okc


def fix(inp, outp):
    data, lines = parse(inp)
    val = '%04X' % crc16_arc(data)
    res, done = [], False
    for l in lines:
        if l.startswith(b'$CHECKSUMME'):
            res.append(('$CHECKSUMME %s %s' % (val, mod36(val))).encode())
            done = True
        else:
            res.append(l)
    if not done:
        sys.exit('Keine $CHECKSUMME-Zeile in %s - nichts berichtigt.' % inp)
    open(outp, 'wb').write(b'\r\n'.join(res) + b'\r\n')
    print('%s -> %s   $CHECKSUMME %s %s' % (inp, outp, val, mod36(val)))
    check(outp)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'pruefen':
        sys.exit(0 if check(sys.argv[2]) else 1)
    if len(sys.argv) == 4 and sys.argv[1] == 'berichtigen':
        fix(sys.argv[2], sys.argv[3]); sys.exit(0)
    print(__doc__)
