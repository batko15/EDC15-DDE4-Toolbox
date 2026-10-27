# EDC15-DDE4-Toolbox

**Werkzeugkasten für Bosch DDE4 (EDC15C4) im BMW M57 / Land Rover Range Rover L322 TD6 —
und für die Siemens GS20-Getriebeesteuerung desselben Fahrzeugs.**

Entstanden aus einem echten Projekt: 2003 Range Rover Vogue L322, BMW M57 TD6 3.0d.
Enthält die erprobte Pipeline **Lesen → Diff → Transplantat → QA → Prüfsummen-Audit → Full-Flash**
als wiederverwendbares Kommandozeilen-Werkzeug, die Reversing-Dokumentation der
EDC15C4-Prüfsummen-Slots sowie den **vollständigen, API-verifizierten GitHub-Tool-Katalog**
für Steuergeräte-Arbeit (`docs/TOOL-KATALOG.md`, ~55 direkte Links).

Schwesterprojekt: **[batko15/QFLASH21](https://github.com/batko15/QFLASH21)** — komplette
Diagnose- & Flash-App (K-Line/KWP2000, Web Serial, PWA + Android-APK) für genau dieses Steuergerät.

---

## Schnellstart

```bash
git clone https://github.com/batko15/EDC15-DDE4-Toolbox.git
cd EDC15-DDE4-Toolbox
python3 edc15toolbox.py --help
```

Keine Abhängigkeiten — reines Python 3.8+.

```bash
# 1) Datei identifizieren (512K-Full-Flash vs 48K-Cal-Container, SW-Nummer, Marker, Entropie)
python3 edc15toolbox.py analyze mein_readout.bin

# 2) Ziel vs Spender vergleichen
python3 edc15toolbox.py diff ziel.bin spender.bin --json diff.json

# 3) Record-Kette des DDE4-Cal-Containers parsen (Kurven/Achsen)
python3 edc15toolbox.py records cal_48k.bin --json records.json

# 4) Transplantat bauen (Spender-Maps -> Ziel, Schutz-Zonen per JSON)
python3 edc15toolbox.py port ziel.bin spender.bin \
        --map configs/l322_td6_1037351777_transplantA.json \
        --out transplant_full.bin --report build_report.json

# 5) QA: nur freigegebene Regionen geändert? Schutz-Zonen intakt?
python3 edc15toolbox.py verify ziel.bin transplant_full.bin --report build_report.json

# 6) Prüfsummen-Slot-Audit (vor/nach kommerzieller Korrektur)
python3 edc15toolbox.py slot-audit neu.bin referenz.bin

# 7) CAL in 512K-Basis einbetten + SHA256SUMS
python3 edc15toolbox.py full-flash basis_512k.bin cal_48k.bin --out full.bin --sums SHA256SUMS.txt
```

**Regression (bewiesen):** Schritt 4 mit der mitgelieferten Konfiguration reproduziert das
ausgelieferte L322-TD6-Transplantat (SW 1037351777 ← 330D 1600BAR 1037351761) **byteidentisch**.

---

## Repo-Aufbau

```
edc15toolbox.py              Einheits-CLI (8 Unterkommandos, getestet)
configs/                     Map-/Schutz-Zonen-JSONs (L322-TD6-Transplantat)
tools/
  l322_edc15c4/              Projektpipeline: Inventur, Records, Build, QA, Varianten,
                             slot_audit, ECU-Modell, Disassembler-Gerüst
  gs20_tcu/                  Siemens GS20: MAX-Patch, MAX3-FINALE-Builder, QA, Prüfsummen-Prüfer
  external/                  Vendored GPL-3: moita420/edc15-tools, Mursteinen/dde4-ecuid
docs/
  TOOL-KATALOG.md            ~55 verifizierte direkte Links (EDC15/DDE4/Checksum/Flash/Diagnose/CAN)
  WORKFLOW-DDE4.md           Schritt-für-Schritt: Lesen -> Full-Flash (3 Flash-Wege)
  CHECKSUMMEN-ARCHITEKTUR-EDC15C4.md   Slot-System, Konstante 0x4711B530, Prüf-Flows
  RESEARCH/                  Zwei GitHub-Deep-Research-Runden (DTCs, EWS, DeepOBD, Web-Serial)
  beispiele/                 Protokolle & Flash-Anleitungen aus dem echten Projekt (VIN-maskiert)
LICENSE                      GPL-3.0 (vendored Teile bleiben GPL-3)
```

## Wichtigster Fachhinweis

**EDC15C4-Prüfsummen sind öffentlich nicht korrigierbar** (Algorithmus im maskierten ROM;
alle öffentlichen EDC15-Familien-Algorithmen — tdi41v2, TDI-V3.1 — passen nachweislich nicht).
Das Repo liefert stattdessen: die komplette **Slot-Architektur** (3 Slots: 0x13FFC / 0x70B7C /
0x7BFFC), den sicheren Korrektur-/Audit-Ablauf und die QA-Regel *„nach der Korrektur darf
exakt nur 0x7BFFC (4 Bytes) geändert sein"*. → `docs/CHECKSUMMEN-ARCHITEKTUR-EDC15C4.md`

## Lizenzen & Credits

- Eigene Werkzeuge: GPL-3.0 (siehe LICENSE).
- `tools/external/edc15-tools` © moita420 (GPL-3) — tdi41v2-Port von VAGEDCSuite (skaldamramra).
- `tools/external/dde4-ecuid` © Mursteinen (GPL-3).
- Fachliche Grundlage: Bosch „EDC 15C Funktionsbeschreibung" B079.CC0 (verlinkt, nicht enthalten).

## Haftungsausschluss

Forschungs-/Bildungszwecke, nur an eigenen oder autorisierten Fahrzeugen, immer mit Backup.
Fehlerhaftes Flashen kann Steuergeräte dauerhaft beschädigen; abgasrelevante Änderungen können
die Zulassung berühren. Nutzung auf eigene Gefahr.
