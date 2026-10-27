#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
edc15toolbox.py — Einheitliches CLI für Bosch EDC15C4/DDE4 (BMW M57, L322 TD6)
==============================================================================
Vereint die in den Projekten L322-TD6 (DDE4-Transplantat, STAGE8-Full-Flash)
erprobten Werkzeuge zu wiederverwendbaren Unterkommandos:

  analyze      Datei identifizieren (Größenklasse, SW-Nummer, Strings, Marker)
  diff         Byte-Diff zweier BINs mit Regionen-Clustering
  records      Record-Kette des DDE4-Cal-Containers parsen (<marker><cnt><axis><data>)
  slot-audit   Prüfsummen-Slot-Audit gegen Referenz (512K, STAGE8-Architektur)
  port         Map-Transplantat bauen: Spender -> Ziel mit Schutz-Zonen (JSON-Map)
  verify       QA: Änderungen nur in freigegebenen Regionen, Schutz-Zonen intakt
  full-flash   CAL-Container in 512K-Basis einbetten + SHA256SUMS
  sha256       Prüfsummen einer Datei

Beispiele:
  python3 edc15toolbox.py analyze mein_full_512k.bin
  python3 edc15toolbox.py diff original.bin tune.bin --json diff.json
  python3 edc15toolbox.py records cal_48k.bin --start auto
  python3 edc15toolbox.py slot-audit flash_korrigiert.bin flash_vorher.bin
  python3 edc15toolbox.py port ziel.bin spender.bin --out transplant.bin \\
          --map configs/l322_td6_1037351777_transplantA.json
  python3 edc15toolbox.py verify original.bin transplant.bin --report qa.json
  python3 edc15toolbox.py full-flash basis_512k.bin cal_48k.bin --out full.bin

Nur für eigene/autorisierte Fahrzeuge zu Forschungs- und Diagnosezwecken.
Keine Bosch-Firmware oder Kalibrierdaten im Repository.
"""
import argparse, hashlib, json, math, os, re, struct, sys
from collections import Counter

# ---------------------------------------------------------------- Konstanten
FULL_512K = 524288          # 0x80000 — Full-Flash 29F400
CAL_48K   = 49152           # 0xC000  — Cal-Container "V2.0"
CAL_OFFSET = 0x70000        # Cal-Block im Full-Flash (DDE4)
SW_CAL_OFF = 0xBFB0         # SW-Nummer (10 ASCII) im 48K-Cal-Container
SW_BOOT_OFF = 0x7BFB4       # SW-Nummer (6 ASCII) im Boot-Read (Mursteinen-Konvention)
SIG1, SIG2 = 0x0B7C, 0xBFFC # 97c1-Signaturfelder im Cal-Container
RECORDS_END = 0xBC00        # danach Identifier/Strings im Cal-Container
# Prüfsummen-Slots DDE4 (STAGE8-Architektur, bewiesen über 24 Referenz-Dumps)
SLOTS = [(0x13FFC, "[0x10000,0x14000)", "Code-Kopf"),
         (0x70B7C, "[0x70000,0x70B80)", "Kodierung"),
         (0x7BFFC, "[0x70B80,0x7C000)", "Datenfenster")]

def die(msg, code=2):
    print(f"FEHLER: {msg}", file=sys.stderr); sys.exit(code)

def load(path):
    if not os.path.isfile(path): die(f"Datei nicht gefunden: {path}")
    with open(path, "rb") as f: return f.read()

def num(x):
    """Hex-String ODER int tolerant in int wandeln (JSON liefert beides)."""
    return x if isinstance(x, int) else int(x, 0)

def md5(b):  return hashlib.md5(b).hexdigest()
def sha256(b): return hashlib.sha256(b).hexdigest()

def entropy(data):
    if not data: return 0.0
    c = Counter(data); n = len(data)
    return -sum((v / n) * math.log2(v / n) for v in c.values())

def diff_regions(a, b, block=16):
    """Zusammenhängende Diff-Regionen in Blockgranularität (bewährt aus l322_ecu_14)."""
    if len(a) != len(b): die(f"Größenunterschied: {len(a)} vs {len(b)}")
    regs, cur = [], None
    for gi in range(len(a) // block):
        off = gi * block
        if a[off:off + block] != b[off:off + block]:
            if cur and cur[1] == off: cur[1] = off + block
            else:
                if cur: regs.append(tuple(cur))
                cur = [off, off + block]
    if cur: regs.append(tuple(cur))
    return regs

def merge_regions(regs, gap=8):
    if not regs: return []
    out, st, pv = [], regs[0][0], regs[0][1] - 1
    for s, e in regs[1:]:
        if s - pv <= gap: pv = e - 1; continue
        out.append((st, pv + 1)); st = pv = s
    out.append((st, pv + 1))
    return out

# ---------------------------------------------------------------- analyze
def cmd_analyze(args):
    for path in args.files:
        d = load(path)
        size = len(d)
        if size == FULL_512K: kind = "FULL-FLASH 512K (29F400)"
        elif size == CAL_48K: kind = "CAL-Container 48K ('V2.0')"
        else: kind = f"unbekannte Größe ({size} B = {hex(size)})"
        print("=" * 78)
        print(f"Datei : {path}")
        print(f"Größe : {size} ({hex(size)})  -> {kind}")
        print(f"MD5   : {md5(d)}")
        print(f"SHA256: {sha256(d)}")
        # SW-Nummer
        if size == CAL_48K:
            sw = d[SW_CAL_OFF:SW_CAL_OFF + 10]
            if sw.isdigit(): print(f"SW-Nummer (Cal @0x{SW_CAL_OFF:05X}): {sw.decode()}")
        if size == FULL_512K:
            sw = d[SW_BOOT_OFF:SW_BOOT_OFF + 6]
            if sw.isdigit(): print(f"SW-Nummer (Boot-Read @0x{SW_BOOT_OFF:05X}): {sw.decode()}")
        # Bosch-/Teilenummern-Strings
        strs = re.findall(rb"[\x20-\x7e]{5,}", d)
        hits = []
        for s in strs:
            t = s.decode("ascii", "ignore")
            if re.search(r"0\s?281\s?\d{3}", t) or re.search(r"\b\d{10}\b", t) \
               or "BOSCH" in t.upper() or re.search(r"EDC15", t, re.I):
                if t not in hits: hits.append(t)
            if len(hits) >= 12: break
        for t in hits: print(f"String: {t[:90]}")
        # C1-Marker-Statistik im Cal-Bereich
        base = 0 if size == CAL_48K else CAL_OFFSET
        end = min(size, base + 0xC000)
        c1 = sum(1 for o in range(base, min(end, base + RECORDS_END) - 4, 2)
                 if (d[o + 1] & 0xFF) == 0xC1 and 1 <= struct.unpack_from("<H", d, o + 2)[0] <= 0x400)
        print(f"xxC1-Marker (plausibel) im Cal-Bereich: {c1}")
        # Entropie-Profil
        step = 0x8000 if size == FULL_512K else 0x4000
        prof = [round(entropy(d[o:o + step]), 2) for o in range(0, size - size % step, step)]
        print(f"Entropie/{step // 1024}K: {prof}")
        print(f"Head64: {d[:64].hex()}")
        print(f"Tail64: {d[-64:].hex()}")
    return 0

# ---------------------------------------------------------------- diff
def cmd_diff(args):
    a, b = load(args.a), load(args.b)
    if len(a) != len(b):
        print(f"GRÖSSENUNTERSCHIED: {len(a)} vs {len(b)} — Regions-Diff übersprungen.")
        return 1
    regs = merge_regions(diff_regions(a, b, args.block), args.gap)
    total = sum(e - s for s, e in regs)
    print(f"Dateien: {args.a} vs {args.b}")
    print(f"Diff-Regionen (Block={args.block}, Gap={args.gap}): {len(regs)}, Bytes gesamt: {total}")
    for s, e in regs[:args.max]:
        print(f"  0x{s:05X}-0x{e:05X}  {e - s:6d} B  | {a[s:min(e, s + 12)].hex()} -> {b[s:min(e, s + 12)].hex()}")
    if len(regs) > args.max: print(f"  ... {len(regs) - args.max} weitere")
    if args.json:
        json.dump({"a": args.a, "b": args.b, "bytes": total,
                   "regions": [{"start": s, "end": e} for s, e in regs]},
                  open(args.json, "w"), indent=1)
        print(f"-> {args.json}")
    return 0 if not regs else 1

# ---------------------------------------------------------------- records
def parse_records(d, start, end):
    """DDE4-Cal-Record-Kette: <marker u16><count u16 LE><axis count×u16><data count×u16>."""
    recs, off = [], start
    while off + 4 <= end:
        marker = struct.unpack_from("<H", d, off)[0]
        cnt = struct.unpack_from("<H", d, off + 2)[0]
        if cnt == 0 or cnt > 0x400:
            return recs, off, f"count={cnt} @0x{off:04X}"
        need = 4 + cnt * 4
        if off + need > end:
            return recs, off, f"überläuft @0x{off:04X}"
        axis = [struct.unpack_from("<H", d, off + 4 + 2 * i)[0] for i in range(cnt)]
        data = [struct.unpack_from("<H", d, off + 4 + 2 * cnt + 2 * i)[0] for i in range(cnt)]
        recs.append({"off": off, "marker": f"{marker:04X}", "cnt": cnt,
                     "axis": axis, "data": data, "size": need})
        off += need
    return recs, off, None

def cmd_records(args):
    d = load(args.file)
    base = 0 if len(d) == CAL_48K else CAL_OFFSET
    end = base + (RECORDS_END if args.end is None else args.end)
    if args.start == "auto":
        best = None
        for start in range(0x10, 0x200, 2):
            recs, nxt, fail = parse_records(d, base + start, end)
            cov = sum(r["size"] for r in recs)
            if best is None or cov > best[0]: best = (cov, base + start, recs, nxt, fail)
        cov, start, recs, nxt, fail = best
    else:
        start = base + int(args.start, 0)
        recs, nxt, fail = parse_records(d, start, end)
        cov = sum(r["size"] for r in recs)
    span = end - start
    print(f"Datei {args.file}: Start 0x{start:04X}, {len(recs)} Records, "
          f"Abdeckung {cov} B ({100 * cov / span:.1f} %), Ende 0x{nxt:04X}, Fail: {fail}")
    print("  Off    Mark  Cnt  Axis(≈)                Data(≈)")
    for r in recs[:args.max]:
        ax = ",".join(map(str, r["axis"][:5])) + ("…" if r["cnt"] > 5 else "")
        da = ",".join(map(str, r["data"][:5])) + ("…" if r["cnt"] > 5 else "")
        print(f"  0x{r['off']:04X} {r['marker']} {r['cnt']:4d}  [{ax}]  [{da}]")
    if len(recs) > args.max: print(f"  ... {len(recs) - args.max} weitere")
    if args.json:
        json.dump(recs, open(args.json, "w"), indent=1)
        print(f"-> {args.json}")
    return 0

# ---------------------------------------------------------------- slot-audit
def cmd_slot_audit(args):
    f_new, f_ref = load(args.new), load(args.ref)
    if len(f_new) != FULL_512K or len(f_ref) != FULL_512K:
        die("beide Dateien müssen 524288 Bytes (512K) sein.")
    print(f"Neu : {args.new}\nRef : {args.ref}\n")
    diffs = [i for i in range(FULL_512K) if f_new[i] != f_ref[i]]
    print(f"Geänderte Bytes gesamt: {len(diffs)}")
    if not diffs:
        print("Dateien sind byteidentisch."); return 0
    regs = merge_regions([(i, i + 1) for i in diffs], 8)
    print("\nDiff-Regionen:")
    for s, e in regs: print(f"  0x{s:05X}-0x{e:05X}  {e - s} B")
    dw_lo, dw_hi = (num(x) for x in args.datawindow.split(":"))
    in_dw = all(dw_lo <= s and e <= dw_hi for s, e in regs)
    only_slot2 = (len(regs) == 1 and regs[0] == (0x7BFFC, 0x7C000))
    print("\nSlot-Status:")
    for off, region, name in SLOTS:
        v_new = struct.unpack_from("<I", f_new, off)[0]
        v_ref = struct.unpack_from("<I", f_ref, off)[0]
        state = "unverändert" if v_new == v_ref else "GEÄNDERT"
        print(f"  {name:14s} @0x{off:05X} {region:18s} {v_new:08X} (ref {v_ref:08X})  {state}")
    if only_slot2:
        print("\nERGEBNIS: PERFECT — nur slot2 (0x7BFFC) wurde korrigiert. Datei flashbereit.")
        return 0
    if in_dw:
        print(f"\nERGEBNIS: Änderungen liegen im Datenfenster ({args.datawindow}).")
        if struct.unpack_from("<I", f_new, 0x7BFFC)[0] == struct.unpack_from("<I", f_ref, 0x7BFFC)[0]:
            print("ACHTUNG: slot2 (0x7BFFC) ist noch WERKSSTAND (STALE) -> Datei noch NICHT flashbar.")
            print("Erst EDC15C4-Prüfsummenmodul (WinOLS-Klasse) laufen lassen, dann erneut prüfen.")
        return 1
    print("\nERGEBNIS: UNERWARTET — Änderungen AUSSERHALB der erlaubten Zonen! Datei NICHT flashen.")
    return 1

# ---------------------------------------------------------------- port
def cmd_port(args):
    cfg = json.load(open(args.map))
    target, donor = load(args.target), load(args.donor)
    cal_off, cal_size = num(cfg.get("cal_offset", CAL_OFFSET)), num(cfg.get("cal_size", CAL_48K))
    if len(target) != FULL_512K: die("Ziel (TARGET) muss 512K-Full-Flash sein.")
    if len(donor) == FULL_512K:
        def donor_byte(rel):
            o = rel
            sh = cfg.get("donor_shift")
            if sh and o >= num(sh["at"]): o = o + num(sh["delta"])
            return donor[cal_off + o]
    elif len(donor) == cal_size:
        def donor_byte(rel):
            o = rel
            sh = cfg.get("donor_shift")
            if sh and o >= num(sh["at"]): o = o + num(sh["delta"])
            return donor[o]
    else:
        die(f"Spendergröße {len(donor)} passt weder zu 512K noch zum Cal-Fenster.")
    keep = [(num(s), num(e)) for s, e in cfg.get("keep", [])]
    ins = cfg.get("insert_keep"); ins = (num(ins[0]), num(ins[1])) if ins else None
    def in_keep(o): return any(s <= o < e for s, e in keep)
    merged = bytearray(target[cal_off:cal_off + cal_size])
    donor_cal = [donor_byte(o) for o in range(cal_size)]
    regs = diff_regions(bytes(merged), bytes(donor_cal))
    copied, kept, changed = [], [], 0
    for s, e in regs:
        if in_keep(s) and in_keep(e - 1):
            kept.append([s, e]); continue
        n = 0
        for o in range(s, e):
            if in_keep(o) or (ins and ins[0] <= o < ins[1]): continue
            if merged[o] != donor_cal[o]: merged[o] = donor_cal[o]; n += 1
        changed += n
        copied.append({"start": s, "end": e, "bytes_changed": n})
    print(f"Regionen gesamt {len(regs)} | kopiert {len(copied)} ({changed} B) | geschützt {len(kept)}")
    for k in kept: print(f"  KEEP 0x{k[0]:04X}-0x{k[1]:04X}")
    out_cal, out_full = bytes(merged), bytearray(target)
    out_full[cal_off:cal_off + cal_size] = merged
    open(args.out, "wb").write(out_full)
    print(f"FULL 512K -> {args.out}  MD5 {md5(out_full)}")
    if args.out_cal:
        open(args.out_cal, "wb").write(out_cal)
        print(f"CAL 48K   -> {args.out_cal}  MD5 {md5(out_cal)}")
    report = {"map": args.map, "copied": copied, "kept": kept,
              "keep_list": [list(k) for k in keep], "insert_keep": list(ins) if ins else None,
              "bytes_changed": changed, "md5_full": md5(out_full), "md5_cal": md5(out_cal)}
    if args.report:
        json.dump(report, open(args.report, "w"), indent=1); print(f"-> {args.report}")
    return 0

# ---------------------------------------------------------------- verify
def cmd_verify(args):
    orig, mod = load(args.original), load(args.modified)
    ok = True
    def check(name, cond, detail=""):
        nonlocal ok
        if not cond: ok = False
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if len(orig) != len(mod): die("Größen unterscheiden sich.")
    print("=== QA 1: Außerhalb des Cal-Fensters identisch? ===")
    check(f"0x00000-0x{CAL_OFFSET:05X} identisch (Code/EWS/Fahrzeugdaten)",
          mod[:CAL_OFFSET] == orig[:CAL_OFFSET])
    tail = CAL_OFFSET + CAL_48K
    check(f"0x{tail:05X}-Ende identisch", mod[tail:] == orig[tail:])
    print("=== QA 2: Änderungen nur in freigegebenen Regionen? ===")
    cal_o, cal_m = orig[CAL_OFFSET:tail], mod[CAL_OFFSET:tail]
    diffs = [i for i in range(CAL_48K) if cal_o[i] != cal_m[i]]
    print(f"  geänderte Bytes im Cal: {len(diffs)}")
    if args.report:
        rep = json.load(open(args.report))
        allowed = [(c["start"], c["end"]) for c in rep.get("copied", [])]
        keep = [(num(s), num(e)) for s, e in rep.get("keep_list", [])]
        ins = rep.get("insert_keep")
        bad = [i for i in diffs if not any(s <= i < e for s, e in allowed)]
        check("alle Änderungen in Kopier-Regionen", not bad, f"{[hex(x) for x in bad[:8]]}")
        bad = [i for i in diffs if any(s <= i < e for s, e in keep)
               or (ins and ins[0] <= i < ins[1])]
        check("Schutz-Zonen unberührt", not bad, f"{[hex(x) for x in bad[:8]]}")
    elif args.allow:
        for lo, hi in args.allow:
            lo, hi = num(lo), num(hi)
            outside = [i for i in diffs if not (lo <= i < hi)]
            check(f"Änderungen ⊆ 0x{lo:05X}-0x{hi:05X}", not outside, f"{[hex(x) for x in outside[:8]]}")
    else:
        print("  (kein --report/--allow gegeben: nur Zonen-1-Prüfung)")
    if args.probe:
        print("=== QA 3: Semantische Stichproben ===")
        for p in args.probe:
            off, n = num(p["offset"]), num(p.get("size", 1))
            want = bytes.fromhex(p["expect"].replace(" ", ""))
            check(p.get("name", f"Probe @0x{off:05X}"),
                  mod[CAL_OFFSET + off:CAL_OFFSET + off + n] == want)
    print(f"\nGESAMT: {'ALLE PASS' if ok else 'FEHLER VORHANDEN'}")
    return 0 if ok else 1

# ---------------------------------------------------------------- full-flash
def cmd_full_flash(args):
    base, cal = load(args.base), load(args.cal)
    if len(base) != FULL_512K: die("Basis muss 512K sein.")
    if len(cal) != CAL_48K: die(f"CAL muss {CAL_48K} B (48K) sein.")
    off = int(args.offset, 0)
    full = bytearray(base); full[off:off + CAL_48K] = cal
    open(args.out, "wb").write(full)
    print(f"Full-Flash -> {args.out}  ({len(full)} B)  MD5 {md5(full)}  SHA256 {sha256(full)}")
    if args.sums:
        with open(args.sums, "w") as f:
            f.write(f"{sha256(full)}  {os.path.basename(args.out)}\n")
            f.write(f"{sha256(cal)}  {os.path.basename(args.cal)}\n")
        print(f"SHA256SUMS -> {args.sums}")
    return 0

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(prog="edc15toolbox", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("analyze", help="BIN identifizieren")
    p.add_argument("files", nargs="+"); p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser("diff", help="Byte-Diff zweier BINs")
    p.add_argument("a"); p.add_argument("b")
    p.add_argument("--block", type=int, default=16)
    p.add_argument("--gap", type=int, default=16)
    p.add_argument("--max", type=int, default=40)
    p.add_argument("--json"); p.set_defaults(fn=cmd_diff)

    p = sub.add_parser("records", help="Cal-Record-Kette parsen")
    p.add_argument("file")
    p.add_argument("--start", default="auto", help="'auto' oder Hex-Offset (relativ zum Cal)")
    p.add_argument("--end", type=lambda x: int(x, 0), default=None)
    p.add_argument("--max", type=int, default=80)
    p.add_argument("--json"); p.set_defaults(fn=cmd_records)

    p = sub.add_parser("slot-audit", help="512K gegen Referenz auditieren (STAGE8-Slots)")
    p.add_argument("new"); p.add_argument("ref")
    p.add_argument("--datawindow", default="0x71838:0x7B1B0")
    p.set_defaults(fn=cmd_slot_audit)

    p = sub.add_parser("port", help="Transplantat bauen (Spender -> Ziel)")
    p.add_argument("target"); p.add_argument("donor")
    p.add_argument("--out", required=True); p.add_argument("--out-cal")
    p.add_argument("--map", required=True); p.add_argument("--report")
    p.set_defaults(fn=cmd_port)

    p = sub.add_parser("verify", help="QA gegen Original + Build-Report")
    p.add_argument("original"); p.add_argument("modified")
    p.add_argument("--report", help="port --report JSON")
    p.add_argument("--allow", nargs="*", help="erlaubte Bereiche LO HI (Hex)")
    p.add_argument("--probe", help="JSON-Datei [{offset,size,expect,name}]")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("full-flash", help="CAL in 512K-Basis einbetten")
    p.add_argument("base"); p.add_argument("cal")
    p.add_argument("--offset", default="0x70000")
    p.add_argument("--out", required=True); p.add_argument("--sums")
    p.set_defaults(fn=cmd_full_flash)

    p = sub.add_parser("sha256", help="SHA256/MD5 von Dateien")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=lambda a: (print(f"{sha256(load(f))}  MD5 {md5(load(f))}  {f}") or 0 for f in a.files) and 0)

    args = ap.parse_args()
    try:
        sys.exit(args.fn(args))
    except BrokenPipeError:
        sys.exit(0)

if __name__ == "__main__":
    main()
