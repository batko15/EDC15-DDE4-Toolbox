import sys

CC = ['UC','NET','Z','NZ','V','NV','N','NN','C','NC','SGT','SLE','SLT','SGE','UGT','ULE']

SFR = {0x00:'DPP0',0x01:'DPP1',0x02:'DPP2',0x03:'DPP3',0x04:'CSP',0x06:'MDH',0x07:'MDL',
       0x08:'CP',0x09:'SP',0x0A:'STKOV',0x0B:'STKUN',0x0F:'PSW',0x10:'ZEROS',0x11:'ONES'}


def reg(r, byte=False):
    if r >= 0xF0:
        n = r & 0x0F
        if byte:
            return ('RL%d' % (n // 2)) if n % 2 == 0 else ('RH%d' % (n // 2))
        return 'R%d' % n
    if r < 0x80:
        a = 0xFE00 + 2 * r
        if r in SFR:
            return SFR[r]
    else:
        a = 0xFF00 + 2 * (r - 0x80)
    return 'sfr[%04X]' % a


def memstr(a):
    return '[%04X]' % a


def bitname(off):
    if off >= 0xF0:
        return 'R%d' % (off & 0x0F)
    if off < 0x80:
        return '%04X' % (0xFD00 + 2 * off)
    return '%04X' % (0xFF00 + 2 * (off - 0x80))


def dis(d, base, start, end):
    i = start
    out = []
    while i < end:
        pc = i
        op = d[i]
        b = d[i + 1] if i + 1 < len(d) else 0
        L = 2
        w = lambda k: d[i + k] | (d[i + k + 1] << 8)
        hi = op & 0xF0
        lo = op & 0x0F
        arith = {0x00:'ADD',0x10:'ADDC',0x20:'SUB',0x30:'SUBC',0x40:'CMP',0x50:'XOR',0x60:'AND',0x70:'OR'}
        s = None
        if hi in arith and lo <= 9:
            m = arith[hi]
            B = 'B' if lo % 2 else ''
            if lo in (0, 1):
                if B:
                    s = '%sB %s, %s' % (m, reg(0xF0 | ((b >> 4) & 15), True),
                                        reg(0xF0 | (b & 15), True))
                else:
                    s = '%s R%d, R%d' % (m, (b >> 4) & 15, b & 15)
            elif lo in (2, 3):
                s = '%s%s %s, %s' % (m, B, reg(b, lo == 3), memstr(w(2))); L = 4
            elif lo in (4, 5):
                s = '%s%s %s, %s' % (m, B, memstr(w(2)), reg(b, lo == 5)); L = 4
            elif lo == 6:
                s = '%s %s, #%04X' % (m, reg(b), w(2)); L = 4
            elif lo == 7:
                s = '%sB %s, #%02X' % (m, reg(b, True), d[i + 2]); L = 4
            else:
                n = (b >> 4) & 0x0F
                mo = b & 0x0F
                if mo < 8:
                    src = '#%d' % (mo & 7)
                elif mo < 0x0C:
                    src = '[R%d]' % (mo & 3)
                else:
                    src = '[R%d+]' % (mo & 3)
                dst = reg(0xF0 | n, B == 'B')
                s = '%s%s %s, %s' % (m, B, dst, src)
        elif lo == 0x0D:
            r = b if b < 128 else b - 256
            s = 'JMPR cc_%s, %04X' % (CC[op >> 4], (base + pc + 2 + 2 * r) & 0xFFFF)
        elif op == 0xF0:
            s = 'MOV R%d, R%d' % ((b >> 4) & 15, b & 15)
        elif op == 0xF1:
            s = 'MOVB %s, %s' % (reg(0xF0 | ((b >> 4) & 15), True), reg(0xF0 | (b & 15), True))
        elif op == 0xF2:
            s = 'MOV %s, %s' % (reg(b), memstr(w(2))); L = 4
        elif op == 0xF3:
            s = 'MOVB %s, %s' % (reg(b, True), memstr(w(2))); L = 4
        elif op == 0xF6:
            s = 'MOV %s, %s' % (memstr(w(2)), reg(b)); L = 4
        elif op == 0xF7:
            s = 'MOVB %s, %s' % (memstr(w(2)), reg(b, True)); L = 4
        elif op == 0xE6:
            s = 'MOV %s, #%04X' % (reg(b), w(2)); L = 4
        elif op == 0xE7:
            s = 'MOVB %s, #%02X' % (reg(b, True), d[i + 2]); L = 4
        elif op == 0xE0:
            s = 'MOV R%d, #%X' % (b & 15, (b >> 4) & 15)
        elif op == 0xE1:
            s = 'MOVB %s, #%X' % (reg(0xF0 | (b & 15), True), (b >> 4) & 15)
        elif op == 0xA8:
            s = 'MOV R%d, [R%d]' % ((b >> 4) & 15, b & 15)
        elif op == 0xA9:
            s = 'MOVB %s, [R%d]' % (reg(0xF0 | ((b >> 4) & 15), True), b & 15)
        elif op == 0x98:
            s = 'MOV R%d, [R%d+]' % ((b >> 4) & 15, b & 15)
        elif op == 0x99:
            s = 'MOVB %s, [R%d+]' % (reg(0xF0 | ((b >> 4) & 15), True), b & 15)
        elif op == 0xB8:
            s = 'MOV [R%d], R%d' % (b & 15, (b >> 4) & 15)
        elif op == 0xB9:
            s = 'MOVB [R%d], %s' % (b & 15, reg(0xF0 | ((b >> 4) & 15), True))
        elif op == 0x88:
            s = 'MOV [-R%d], R%d' % (b & 15, (b >> 4) & 15)
        elif op == 0x89:
            s = 'MOVB [-R%d], %s' % (b & 15, reg(0xF0 | ((b >> 4) & 15), True))
        elif op == 0xC8:
            s = 'MOV [R%d], [R%d]' % ((b >> 4) & 15, b & 15)
        elif op == 0xD8:
            s = 'MOV [R%d+], [R%d]' % ((b >> 4) & 15, b & 15)
        elif op == 0xE8:
            s = 'MOV [R%d], [R%d+]' % ((b >> 4) & 15, b & 15)
        elif op == 0x84:
            s = 'MOV [R%d], %s' % (b & 15, memstr(w(2))); L = 4
        elif op == 0x94:
            s = 'MOV %s, [R%d]' % (memstr(w(2)), b & 15); L = 4
        elif op == 0xA4:
            s = 'MOVB [R%d], %s' % (b & 15, memstr(w(2))); L = 4
        elif op == 0xB4:
            s = 'MOVB %s, [R%d]' % (memstr(w(2)), b & 15); L = 4
        elif op == 0xD4:
            s = 'MOV R%d, [R%d + #%04X]' % ((b >> 4) & 15, b & 15, w(2)); L = 4
        elif op == 0xC4:
            s = 'MOV [R%d + #%04X], R%d' % (b & 15, w(2), (b >> 4) & 15); L = 4
        elif op == 0xF4:
            s = 'MOVB %s, [R%d + #%04X]' % (reg(0xF0 | ((b >> 4) & 15), True), b & 15, w(2)); L = 4
        elif op == 0xE4:
            s = 'MOVB [R%d + #%04X], %s' % (b & 15, w(2), reg(0xF0 | ((b >> 4) & 15), True)); L = 4
        elif op == 0xEC:
            s = 'PUSH %s' % reg(b)
        elif op == 0xFC:
            s = 'POP %s' % reg(b)
        elif op == 0xCC:
            s = 'NOP'
        elif op == 0xDB:
            s = 'RETS'
        elif op == 0xCB:
            s = 'RETI'
        elif op == 0xFB:
            s = 'RETI/RETS?'
        elif op == 0xDA:
            s = 'CALLS %02X, %04X' % (b, w(2)); L = 4
        elif op == 0xFA:
            s = 'JMPS %02X, %04X' % (b, w(2)); L = 4
        elif op == 0xEA:
            s = 'JMPA cc_%s, %04X' % (CC[(b >> 4) & 15], w(2)); L = 4
        elif op == 0xCA:
            s = 'CALLA cc_%s, %04X' % (CC[(b >> 4) & 15], w(2)); L = 4
        elif op == 0xBB:
            r = b if b < 128 else b - 256
            s = 'CALLR %04X' % ((base + pc + 2 + 2 * r) & 0xFFFF)
        elif op == 0x9B:
            s = 'TRAP #%02X' % (b >> 1)
        elif op == 0xC6:
            s = 'SCXT %s, #%04X' % (reg(b), w(2)); L = 4
        elif op in (0x8A, 0x9A, 0xAA, 0xBA):
            nm = {0x8A:'JB',0x9A:'JNB',0xAA:'JBC',0xBA:'JNBS'}[op]
            bitoff = b
            bit = (d[i + 3] >> 4) & 15
            r = d[i + 2]
            r = r if r < 128 else r - 256
            ba = bitname(bitoff)
            s = '%s %s.%d, %04X' % (nm, ba, bit, (base + pc + 4 + 2 * r) & 0xFFFF); L = 4
        elif op in (0x0A, 0x1A):
            nm = 'BFLDL' if op == 0x0A else 'BFLDH'
            s = '%s %s, #%02X, #%02X' % (nm, bitname(b), d[i + 2], d[i + 3]); L = 4
        elif op in (0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A):
            nm = {0x2A:'BCMP',0x3A:'BMOVN',0x4A:'BMOV',0x5A:'BAND',0x6A:'BOR',0x7A:'BXOR'}[op]
            s = '%s %s.%d, %s.%d' % (nm, bitname(b), (d[i + 3] >> 4) & 15, bitname(d[i + 2]), d[i + 3] & 15); L = 4
        elif lo == 0x0E:
            s = 'BCLR %s.%d' % (bitname(b), op >> 4)
        elif lo == 0x0F:
            s = 'BSET %s.%d' % (bitname(b), op >> 4)
        elif op in (0x0C,0x1C,0x2C,0x3C,0x4C,0x5C,0x6C,0x7C,0xAC,0xBC):
            nm = {0x0C:'ROL',0x1C:'ROL',0x2C:'ROR',0x3C:'ROR',0x4C:'SHL',0x5C:'SHL',
                  0x6C:'SHR',0x7C:'SHR',0xAC:'ASHR',0xBC:'ASHR'}[op]
            imm = op in (0x1C, 0x3C, 0x5C, 0x7C, 0xBC)
            s = '%s R%d, %s' % (nm, b & 15, ('#%X' % ((b >> 4) & 15)) if imm else 'R%d' % ((b >> 4) & 15))
        elif op == 0xD7:
            irang = ((b >> 4) & 3) + 1
            kind = 'EXTS' if (b & 0x80) else 'EXTP'
            if b & 0x40:
                kind += 'R'
            s = '%s #%04X, #%d' % (kind, w(2), irang); L = 4
        elif op == 0xDC:
            irang = ((b >> 4) & 3) + 1
            kind = 'EXTS' if (b & 0x80) else 'EXTP'
            if b & 0x40:
                kind += 'R'
            s = '%s R%d, #%d' % (kind, b & 15, irang)
        elif op == 0x81:
            s = 'NEGB %s' % reg(0xF0 | (b & 15), True)
        elif op == 0x91:
            s = 'CPL R%d' % (b & 15)
        elif op == 0xA1:
            s = 'NEG R%d' % (b & 15)
        elif op == 0xB1:
            s = 'CPLB %s' % reg(0xF0 | (b & 15), True)
        else:
            s = 'db %02X %02X' % (op, b)
        raw = ' '.join('%02X' % x for x in d[i:i + L])
        out.append('%06X  %04X  %-12s %s' % (pc, (base + pc) & 0xFFFF, raw, s))
        i += L
    return out


if __name__ == '__main__':
    f = sys.argv[1]
    start = int(sys.argv[2], 16)
    end = int(sys.argv[3], 16)
    d = open(f, 'rb').read()
    # flash file offset x -> CPU address 0x80000 + x
    for line in dis(d, 0x80000, start, end):
        print(line)
