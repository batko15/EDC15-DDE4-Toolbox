# Prüfsummen-Architektur DDE4 / EDC15C4 (L322 TD6, Full-Flash 512K)

**Quelle:** STAGE8-Tiefenanalyse (Task 9) — Disassembler-Arbeit am echten ROM, verifiziert gegen
24 Referenz-Dumps (Mursteinen-Sammlung + eigene Reads) und das Werkspaar `351777_ori` ↔ `KENAN`.

## 1. Das Slot-System

Die DDE4 prüft den 512-KB-Flash in **drei unabhängigen Slots** (jew. 32-Bit-Wort, little-endian,
am Ende der Region):

| Slot | Adresse | Abgedeckte Region | Verhalten nach Cal-Änderung |
|---|---|---|---|
| Code-Kopf | `0x13FFC` | `[0x10000, 0x14000)` | unverändert lassen (Code unberührt) |
| Kodierung | `0x70B7C` | `[0x70000, 0x70B80)` | unverändert lassen (Kodierbereich unberührt) |
| **Datenfenster** | **`0x7BFFC`** | `[0x70B80, 0x7C000)` | **muss nach jeder Datenänderung neu gesetzt werden** |

Beweispaar (Werkspaar `351777_ori` ↔ `KENAN`-Tune): 6 geänderte Map-Wörter + **nur** slot2
neu gesetzt — slot1/0x13FFC blieben unverändert gültig → Slots sind voneinander unabhängig.

## 2. Der Algorithmus (was wir wissen)

- ROM-Kette mit 16-Bit-Rotationen und Zielkonstante **`0x4711B530`** (erkennbar als
  `SUB R1, #0xB530` / `SUBC R6, #0x4711`).
- 3 Prüf-Flows im Code:
  1. **Selbsttest** @ `0x113A0` (Fehlercodes 0x28/0x2B bei Misserfolg),
  2. **Tail-Verify** @ `0x7E6E0` (tabellengesteuert),
  3. **Hintergrundmonitor** @ `0x11AD2` (prüft im Betrieb).
- Der eigentliche Algorithmus liegt **im maskierten ROM** und ist nicht aus dem Flash
  rekonstruierbar. Brute-Force gegen 46 Bilder (VAG-tdi41-Port, TDI-V3.1, 64+ Skeleton-Varianten,
  CRC16-Gesamtraum, Additiv-Familien) ergab **null Treffer** — konsistent zur Fachlage:
  EDC15C4 ist öffentlich nur über kommerzielle Module (WinOLS-Klasse) korrigierbar.

## 3. Sicheres Vorgehen nach jeder Datenänderung

```bash
# 1) Audit VOR der Korrektur: Änderungen müssen im Datenfenster liegen,
#    slot2 ist noch Werkswert (STALE):
python3 edc15toolbox.py slot-audit NEU.bin ORIGINAL.bin
#    -> "Änderungen im Datenfenster ... slot2 noch STALE, NICHT flashbar"

# 2) Kommerzielles EDC15C4-Modul laufen lassen (z. B. WinOLS EDC15-Modul)

# 3) Audit NACH der Korrektur: Es darf GENAU 0x7BFFC..0x7C000 (4 Bytes) differieren:
python3 edc15toolbox.py slot-audit NEU_KORRIGIERT.bin NEU.bin
#    -> "PERFECT — nur slot2 wurde korrigiert. Datei flashbereit."
```

Alles anderes als „nur slot2" nach Schritt 3 bedeutet Fehlverhalten des Korrekturmoduls
→ Datei **nicht** flashen. Das ist der QA-Standard, mit dem auch die STAGE8-Lieferung geprüft
wurde (`tools/l322_edc15c4/slot_audit.py`).

## 4. Verwandte (nicht-EDC15C4) Algorithmen im Repo

| Familie | Werkzeug | Regionen (Beispiel 512 KB) |
|---|---|---|
| EDC15V/VM/P „tdi41v2" | `tools/external/edc15-tools/edc15_checksum.py` | Regionen `0x10000/0x14000/0x58000/0x58B80/0x64000/0x70000/0x70B80/0x7C000`, Summen am Regionen-Ende |
| EDC15M „TDI V3.1" | https://github.com/mancube/EDC15M-Checksum-Corrector | `0x3FBFC` über `[0x38B80,0x3FC00)`, `0x13FFC` über `[0x10000,0x14000)` |
| DDE4-**CR2-Bankprüfsummen** (QFLASH21, 16-KiB-Bänke, 2×16-Bit-Summenwörter) | https://github.com/batko15/QFLASH21 (`src/lib/kwp/checksum.ts`) | Lesen/Korrigieren der Bänke mit Vorher/Nachher |
