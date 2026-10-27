# Workflow DDE4/EDC15C4: vom Lesen zum flashfähigen Full-Flash

Erprobte Pipeline aus den L322-TD6-Projekten (Transplantat 330D 1600BAR → SW 1037351777,
STAGE8-Full-Flash). Jeder Schritt ist mit `edc15toolbox.py` nachfahrbar.

## Schritt 0 — Backup (niemals überspringen)

```bash
cp ORIGINAL_READOUT.bin BACKUP_ORIGINAL.bin
python3 edc15toolbox.py sha256 BACKUP_ORIGINAL.bin   # Prüfsummen notieren
```

Der Readout ist der einzige Rückweg. Ohne Backup: kein Flashen.

## Schritt 1 — Identifizieren

```bash
python3 edc15toolbox.py analyze DATEI.bin
```

Erwartbar: `FULL-FLASH 512K (29F400)` mit SW-Nummer @0x7BFB4 (Boot-Read-Konvention) oder
`CAL-Container 48K ('V2.0')` mit SW-Nummer @0xBFB0. Die SW-Nummer (z. B. `1037351777`)
entscheidet, welche Spender-/Ziel-Kombinationen strukturell kompatibel sind.

## Schritt 2 — Verstehen

```bash
python3 edc15toolbox.py diff ZIEL.bin SPENDER.bin --json diff.json --max 60
python3 edc15toolbox.py records CAL_48K.bin --json records.json
```

- `diff` zeigt die Differenz-Regionen (Block-Cluster) — beim Transplantat waren es 175 Regionen
  / 10 868 Bytes im Cal-Fenster.
- `records` parst die Record-Kette `<marker><count><axis><data>` (xxC1-Marker = Kurven,
  9ada/beda = Pedal-/Druck-Records). Die 6 großen Karten mit identischer Drehzahlachse
  (363–3930) sind die per-Gang-Kernkarten.

## Schritt 3 — Transplantat bauen (`port`)

Map-JSON anlegen (Vorlage: `configs/l322_td6_1037351777_transplantA.json`):

- `donor_shift`: falls Ziel/Spender strukturell um N Bytes ab Offset X differieren
  (RR-Version: +2 Wörter @0x03862 → Spender shift −4 ab 0x3866),
- `keep`: Schutz-Zonen, die **ziel-original** bleiben (Header, Signaturen 97c1 @0xB70/0xBFF0,
  Sensor-Records, DTC/Monitor-Konfig, EGR-Verdachtszone, **SW-Nummer**, Insertion),
- alles andere wird aus dem Spender übernommen, sofern es differiert.

```bash
python3 edc15toolbox.py port ZIEL.bin SPENDER.bin \
    --map configs/l322_td6_1037351777_transplantA.json \
    --out TRANSPLANT_FULL_512K.bin --out-cal TRANSPLANT_CAL_48K.bin \
    --report build_report.json
```

Regression: dieser Befehl reproduziert das ausgelieferte L322-Transplantat **byteidentisch**.

## Schritt 4 — QA (`verify`)

```bash
python3 edc15toolbox.py verify ZIEL.bin TRANSPLANT_FULL_512K.bin --report build_report.json
```

Prüft: Code/EWS/Fahrzeugdaten (0x00000–0x70000 und 0x7C000–Ende) byteidentisch,
Änderungen nur in Kopier-Regionen, Schutz-Zonen unberührt. Optional semantische Stichproben
über `--probe` (z. B. Rail-Druck-Limit-Record `bedb` = 18000).

## Schritt 5 — Prüfsummen

```bash
python3 edc15toolbox.py slot-audit TRANSPLANT_FULL_512K.bin ZIEL.bin
```

Erwartung vor Korrektur: Änderungen im Datenfenster, **slot2 @0x7BFFC noch STALE → nicht
flashbar**. Dann kommerzielles EDC15C4-Modul (WinOLS-Klasse) laufen lassen und erneut:

```bash
python3 edc15toolbox.py slot-audit TRANSPLANT_KORRIGIERT.bin TRANSPLANT_FULL_512K.bin
# -> "PERFECT — nur slot2 wurde korrigiert. Datei flashbereit."
```

Details: `docs/CHECKSUMMEN-ARCHITEKTUR-EDC15C4.md`.

## Schritt 6 — Flashen (drei erprobte Wege)

| Weg | Werkzeug | Hinweis |
|---|---|---|
| K-Line/KWP2000 über OBD | **QFLASH21** (https://github.com/batko15/QFLASH21) | FULL-512K-Lesen/Schreiben, Spannungs-Gate ≥ 12 V, Backup-Pflicht, Protokoll-Log |
| Bench/Boot (Sicherungskopie-Erzeugung) | BDM/Boot-Setup wie bei den Mursteinen-Dumps | wenn OBD-Schreiben verweigert wird |
| Kommerzielle Tools | Galletto/MPPS-Klasse + WinOLS | Checksummen-Korrektur meist im selben Tool |

Nach dem Flashen: erst Leerlauf-/Probefahrt-Protokoll (siehe `docs/beispiele/FLASH_ANLEITUNG.txt`),
Rückweg ist immer `BACKUP_ORIGINAL.bin`.

## Rechtliches

Nur an eigenen/autorisierten Fahrzeugen, zu Forschungs- und Bildungszwecken. Abgasrelevante
Änderungen können die Straßenverkehrs-Zulassung berühren; Prüfsysteme (TÜV/HU) und lokale
Gesetze beachten. Nutzung auf eigene Gefahr — ein fehlgeschlagener Flash kann die ECU bricken.
