#!/usr/bin/env python3
"""
L322 TD6 / Bosch DDE4 (EDC15C4) - SLOT-AUDIT
=============================================
Prueft eine 512K-Full-Flash-Datei gegen das Original (altes Steuergaet):

  Modus 1 (Pruefung der STAGE8-Basis):
     python3 slot_audit.py FULL_FLASH.bin ORIGINAL.bin
     -> verifiziert: Programm/Kodierung/EWS/VIN identisch,
        Aenderungen NUR im Datenfenster 0x71838..0x7B1B0, slot1 unveraendert,
        slot2 (0x7BFFC) == Werkswert (STALE, wartet auf Korrektur).

  Modus 2 (Pruefung NACH Pruefsummen-Korrektur, z.B. WinOLS EDC15C4-Modul):
     python3 slot_audit.py FULL_FLASH_KORRIGIERT.bin FULL_FLASH.bin
     -> verifiziert: das Korrekturmodul hat GENAU 4 Bytes an 0x7BFFC
        geaendert und sonst NICHTS. Alles andere = Modul-Fehlverhalten.

Pruefsummen-Slots der DDE4 (bewiesen ueber 24 Referenz-Dumps + Werkspair 351777/KENAN):
  slot Code-Kopf    0x13FFC  Region [0x10000,0x14000)   (aktiv, hier unveraendert)
  slot Kodierung    0x70B7C  Region [0x70000 ,0x70B80)  (aktiv, hier unveraendert)
  slot Datenfenster 0x7BFFC  Region [0x70B80 ,0x7C000)  (aktiv, MUSS nach Datenände-
                                                         rung vom Modul neu gesetzt
                                                         werden - Algorithmus liegt im
                                                         maskierten ROM, nicht publi-
                                                         ziehbar)
"""
import sys, struct

SLOTS = [(0x13FFC, "[0x10000,0x14000)", "Code-Kopf"),
         (0x70B7C, "[0x70000,0x70B80)", "Kodierung"),
         (0x7BFFC, "[0x70B80,0x7C000)", "Datenfenster")]

def main():
    if len(sys.argv) != 3:
        print(__doc__); return 2
    f_new, f_ref = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
    if len(f_new) != 524288 or len(f_ref) != 524288:
        print("FEHLER: beide Dateien muessen 524288 Bytes (512K) sein."); return 2
    print(f"Neu : {sys.argv[1]}")
    print(f"Ref : {sys.argv[2]}\n")

    diffs = [i for i in range(524288) if f_new[i] != f_ref[i]]
    print(f"Geaenderte Bytes gesamt: {len(diffs)}")
    if not diffs:
        print("Dateien sind byteidentisch."); return 0

    # diff regions
    regs, st, pv = [], diffs[0], diffs[0]
    for i in diffs[1:]:
        if i - pv <= 8: pv = i; continue
        regs.append((st, pv + 1)); st = pv = i
    regs.append((st, pv + 1))

    in_datawindow = all(0x71838 <= s and e <= 0x7B1B0 for s, e in regs)
    only_slot2 = (len(regs) == 1 and regs[0] == (0x7BFFC, 0x7C000))

    print("\nDiff-Regionen:")
    for s, e in regs:
        print(f"  0x{s:05X}-0x{e:05X}  {e-s} B")

    print("\nSlot-Status:")
    ok = True
    for off, region, name in SLOTS:
        v_new = struct.unpack("<I", f_new[off:off+4])[0]
        v_ref = struct.unpack("<I", f_ref[off:off+4])[0]
        state = "unveraendert" if v_new == v_ref else "GEAENDERT"
        print(f"  {name:14s} @0x{off:05X} {region:18s} {v_new:08X} (ref {v_ref:08X})  {state}")

    if only_slot2:
        print("\nERGEBNIS: PERFECT - nur slot2 (0x7BFFC) wurde korrigiert.")
        print("Die Datei ist bereit zum Flashen (Rueckweg: ORIGINAL-Backup).")
        return 0
    if in_datawindow and not only_slot2:
        print("\nERGEBNIS: Aenderungen liegen im Datenfenster (0x71838..0x7B1B0).")
        if struct.unpack("<I", f_new[0x7BFFC:0x7C000])[0] == struct.unpack("<I", f_ref[0x7BFFC:0x7C000])[0]:
            print("ACHTUNG: slot2 (0x7BFFC) ist noch WERKSSTAND -> die Datei ist")
            print("noch NICHT flashbar. Erst Pruefsummen-Modul (EDC15C4) laufen lassen.")
        return 1

    print("\nERGEBNIS: UNERWARTET - Aenderungen AUSSERHALB der erlaubten Zonen!")
    print("  Erlaubt waeren nur: Datenfenster 0x71838..0x7B1B0 bzw. nach der")
    print("  Korrektur GENAU 0x7BFFC..0x7C000. Datei NICHT flashen.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
