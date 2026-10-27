# Tool-Katalog: EDC15/DDE4, GS20 & Fahrzeug-Elektronik

**Stand:** 27.10.2026 · **Alle Links verifiziert über die GitHub-API** (Sterne/Lizenz Stand des Katalog-Datums).
Kategorien: Eigene Werkzeuge → EDC15C4/DDE4-Kern → EDC15-Familie → Prüfsummen → Flashen & Protokolle → BMW-Diagnose → Editoren & Mapping → CAN & Security → Android/K-Line → Kommerziell → Wissen.

---

## A. Eigene Werkzeuge (dieses Repo)

| Werkzeug | Zweck |
|---|---|
| `edc15toolbox.py` | Einheits-CLI: `analyze` · `diff` · `records` · `slot-audit` · `port` · `verify` · `full-flash` · `sha256` — regressionstestet gegen das ausgelieferte L322-Transplantat (byteidentisch) |
| `configs/l322_td6_1037351777_transplantA.json` | Schutz-Zonen-/Shift-Konfig des L322-TD6-Transplantats (SW 1037351777 ← 330D 1600BAR 1037351761) |
| `tools/l322_edc15c4/` | Projektpipeline: Inventur, Record-Scan, Transplantat-Bau, QA, Varianten B, Slot-Audit, ECU-Modell, Disassembler-Gerüst |
| `tools/gs20_tcu/` | Siemens GS20-Getriebe (L322): MAX-Patch, MAX3-FINALE-Builder, QA, Prüfsummen-Prüfer |
| `tools/external/edc15-tools/` | Vendored: moita420/edc15-tools (GPL-3) — tdi41v2-Prüfsumme, C166-Disassembler, KWP1281-Probe |
| `tools/external/dde4-ecuid/` | Vendored: Mursteinen EcuID (GPL-3) — SW-Nummer aus Boot-Read @0x7BFB4 |
| `docs/CHECKSUMMEN-ARCHITEKTUR-EDC15C4.md` | Reversing-Ergebnis: Slot-System, Konstante 0x4711B530, Prüf-Flows |
| `docs/WORKFLOW-DDE4.md` | Der komplette Lesen→Diff→Port→QA→Checksum→Flash-Ablauf |

**Schwesterprojekt (separates Repo, gehört dazu):**
- **batko15/QFLASH21** — https://github.com/batko15/QFLASH21 — komplette DDE4-Diagnose- & Flash-App (K-Line/KWP2000, Web Serial, PWA, Android-APK): 5-Baud-Init (Adresse 0x12, Keywords 0x45 0x05), Fehlerspeicher normal+Schatten (0x18 FF00/FD00), 51 EDC15-DTC-Texte, 5 Messwertblöcke (0x03/0x07/0x13/0x15/0x17), Jobs (0x11/0x30/0x31), FULL-512K/CAL-48K-Lesen, CR2-Bankprüfsummen, Simulator, DeepOBD-Konfigsammlung.

---

## B. EDC15C4 / DDE4-Kern (BMW M57, L322 TD6)

| Repo | ★ | Lizenz | Inhalt |
|---|---|---|---|
| https://github.com/GabrielStanescu/BMW_M57_EDC15C4 | 6 | — | **Kernreferenz:** offizielle Bosch „EDC 15C Funktionsbeschreibung" B079.CC0 (PDF, BMW Y 445 S00 003) + WinOLS-Projekte (damos_project.ols, remap_project.ols) + Original-Flash 330d 184 PS (SW 1037351761) |
| https://github.com/Mursteinen/BMW-DDE4-EDC15c4-EcuID | 2 | GPL-3 | 23 echte EDC15C4-Dumps (BMW 4.0D, Mini 1.4d, Rover 75 CDTI, Freelander 2.0) + 2 IMMO-off-Boot-Read-Diffs + SW-Nummer-Reader (Offset 0x7BFB4) |
| https://github.com/batko15/QFLASH21 | 0 | — | DDE4-Diagnose & Flash (s. o.) |

---

## C. EDC15-Familie allgemein (VAG/PSA/M — Methodik übertragbar)

| Repo | ★ | Lizenz | Inhalt |
|---|---|---|---|
| https://github.com/moita420/edc15-tools | 0 | GPL-3 | tdi41v2-Prüfsumme verify/fix (512 KB), C166-Disassembler, KWP1281-Probe — **in diesem Repo vendored** |
| https://github.com/mancube/EDC15M-Checksum-Corrector | — | — | EDC15M „TDI V3.1"-Prüfsumme (CLI + PySide6-GUI, Selbsttest) — Algorithmus-Doku in `docs/REVERSE-ENGINEERING.md` |
| https://github.com/skaldamramra/VAGEDCSuite | 35 | GPL-3 | Originale C#-Quelle des tdi41-Algorithmus (EDC15V/VM/P) |
| https://github.com/NickTullos/edc15vm-flash-editor | 6 | — | .NET-7: ALH EDC15V/VM-Flash-Inspektion, automatische DTC-Entdeckung in BINs |
| https://github.com/krook1024/edc15-eoi | 17 | — | Einspritzbeginn-Rechner (EOI) |
| https://github.com/krook1024/edc15-swiss-knife | 7 | — | EDC15-Werkzeugkasten |
| https://github.com/krook1024/edcp | 3 | — | MSA15/EDC15-Parser |
| https://github.com/mtx-electronics/vag-checksum-fix | 2 | — | VAG EDC15-Prüfsumme (Referenzpfad) |
| https://github.com/paceworx-store/EDC15C13-Checksum-Correction | 0 | — | EDC15C13 (C-Familie!) — Ansatz auf C4 testbar |
| https://github.com/marcelweinbach93-stack/VAGSUITE-NextGen | 3 | — | EDC15/16/17-Suite (jung, beobachten) |
| https://github.com/muki01/Bosch_EDC15_EEPROM_Tool | 12 | — | EEPROM-Tool (24C04): IMMO-Status, Login — VAG |
| https://github.com/RJ-6463/Bosch_EDC15_EEPROM_Tool | 4 | — | Fork, aktiv weiterentwickelt |
| https://github.com/LeZed97/ZedSuite | 175 | — | Freier Kennfeld-Editor: beliebige BINs, Auto-Detection EDC15/16 (100 % lokal) |

---

## D. Prüfsummen weiterer ECU-Familien

| Repo | ★ | Lizenz | Inhalt |
|---|---|---|---|
| https://github.com/ConnorHowell/medc17-checksum-tool | 59 | MIT | Analyzer/Corrector Bosch MED17/EDC17 |
| https://github.com/KWR666/Checksum-Corrector | 0 | — | MED7/MED9-Prüfsummen **per Handy** |
| https://github.com/bri3d/VW_Flash | 566 | — | VW-UDS-Flashing: Kompression, Verschlüsselung, Checksummen — Architektur-Referenz |

> **EDC15C4-Status:** Es gibt **kein öffentliches** EDC15C4-Prüfsummenmodul. Unsere Reversing-Ergebnisse (Slots, Konstante, Flows) stehen in `docs/CHECKSUMMEN-ARCHITEKTUR-EDC15C4.md`; Korrektur derzeit über WinOLS-EDC15-Modul (kommerziell) — danach mit `edc15toolbox.py slot-audit` prüfen: es darf **nur** 0x7BFFC (4 Bytes) geändert worden sein.

---

## E. Flashen & Protokolle (K-Line/KWP2000/UDS)

| Repo | ★ | Lizenz | Inhalt |
|---|---|---|---|
| https://github.com/ms4x-net/ms4x_flasher | 27 | — | MS4X Flasher: GS20/GS8.60.x/SMG2 lesen+schreiben (unser Getriebe-Weg!), lokale Checksum-Correction |
| https://github.com/dspl1236/VAGFlasher | 28 | MIT | Open-Source VAG ECU/TCU-Flasher (ME17/MED9/ME7/EDC17) |
| https://github.com/DSparks156x/PQ35-Flasher | 0 | — | TP2/KWP2000-Flash VAG PQ35 |
| https://github.com/pandolfipedro/09G-Recovery-VW-AQ250-Flash | 1 | — | Aisin-09G-TCM-Recovery über KWP2000 |
| https://github.com/aster94/Keyword-Protocol-2000 | 327 | — | KWP2000-Arduino-Library (5-Baud/Timeout-Referenz) |
| https://github.com/muki01/OBD2_K-line_Reader | 234 | — | ISO9141/ISO14230-Reader (ESP32/Arduino, 5-Baud + Fast-Init) |
| https://github.com/pylessard/python-udsoncan | 734 | MIT | UDS (ISO-14229) Python-Referenzimplementation |
| https://github.com/oxibus/automotive_diag | 101 | — | Rust-Crate: UDS/KWP2000/OBD-II/DoIP-Parser |
| https://pypi.org/project/isotp/ | — | — | ISO-TP (ISO-15765-2) Python-Modul, Doku: https://python-isotp.readthedocs.io |

---

## F. BMW-Diagnose & Codierung

| Repo/Quelle | ★ | Lizenz | Inhalt |
|---|---|---|---|
| https://github.com/uholeschak/ediabaslib | 939 | — | .NET BMW/VAG-EDIABAS-Interpreter (DS2/DS1/KWP, SGBD-Referenz) |
| https://www.holeschak.de/BmwDeepObd/ | — | — | **Deep OBD for BMW** (App selbst); Konfig-Format .ccpage/.cccfg/.ccpages |
| https://github.com/Dekon01/DeepObdE46Config | 0 | — | Vollständiges BmwDeepObd.xsd + E46-Beispielseiten (Benziner — Struktur-Referenz) |
| https://github.com/kmalinich/deepobd-configs | 9 | — | DeepOBD-XML-Konfigurationen |
| https://github.com/tooming/garagediag | 1 | MIT | K-Line-Diagnose alte BMWs (E39/E87) über K+DCAN |
| https://github.com/dader34/BMWeb | 18 | GPL-3 | BMW-Software-Tools-Sammlung (Windows, reverse engineering) |
| https://github.com/0xDevDav/EWSync | 3 | MIT | BMW EWS/DME-ISN-Synchronisation (DS2 über K-Line) |
| https://github.com/BimmerDock/ESeriesSwitch | 1 | MIT | One-Click-Umschalter für E-Reihen-Codier-Tools |
| https://github.com/mushitaro/E46M3-Monitoring | 0 | MIT | E46-M3-Diagnose im Browser |
| **BMW Standard Tools 2.12.8** (INPA/NCS Expert/WinKFP/Tool32) | — | — | https://bimmerpro.de/en/products/bmw-standard-tools-inpa-ncs-expert-download · DIY-Setup: https://www.e90post.com/forums/showthread.php?t=1204192 |

---

## G. Editoren, Mapping-Definitionen & Kennfelder

| Quelle | ★ | Typ | Inhalt |
|---|---|---|---|
| https://www.tunerpro.net | — | Gratis | **TunerPro 5 + XDF-Definitionen** — der Standard-Editor für unsere GS20-/EDC15-Arbeit; Forum: http://forum.tunerpro.net |
| https://www.ms4x.net | — | Community | MS4X-Wiki, **Definition Files (GS20-XDF von „olza/Blu302")**, ms4x_flasher |
| https://oldskulltuning.com/news/ | — | Blog | Laufend neue XDF-Definitionen (ECU+TCU) für TunerPro |
| https://github.com/RomRaider/RomRaider | 373 | GPL | Open-Source-Tuning-Suite (Editor+Logger, Subaruy — Architektur-Referenz) |
| https://github.com/LeZed97/ZedSuite | 175 | — | (s. Kategorie C) Auto-Detection-Editor |
| https://github.com/alexyss63-collab/AEON-Automotive-Binary-Lab | 3 | — | ECU-Reverse-Engineering-Binärwerkzeuge (jung) |
| https://www.evc.de | — | Kommerziell | **WinOLS** — für EDC15C4-Prüfsummen aktuell Pfad der Wahl (EDC15-Modul) |
| https://www.alientech-tools.com | — | Kommerziell | ECM Titanium (Damos-DB) |
| https://www.swiftec.org | — | Kommerziell | Swiftec (MAF-off/EGR/DTC-Module) |

---

## H. CAN, Security & Curated Lists

| Repo | ★ | Lizenz | Inhalt |
|---|---|---|---|
| https://github.com/iDoka/awesome-canbus | 3525 | CC0 | Awesome CAN-Bus: Tools, Hardware, Reverse Engineering |
| https://github.com/jaredthecoder/awesome-vehicle-security | 4729 | — | Awesome Vehicle Security (ECU-Kapitel!) |
| https://github.com/iDoka/awesome-automotive-can-id | 1007 | CC0 | CAN-ID-/Payload-Datenbank verschiedener Marken |
| https://github.com/cantools/cantools | 2305 | MIT | DBC/ARXML-Kodieren/Dekodieren, CLI |
| https://github.com/linux-can/can-utils | 2941 | GPL | SocketCAN-Standardwerkzeuge |
| https://github.com/collin80/SavvyCAN | 1891 | — | Qt-CAN-Sniffer/Reverse-Engineering (EVTV) |
| https://github.com/commaai/panda | 1707 | — | Universal-CAN-Hardware+FW (comma.ai) |
| https://github.com/dschanoeh/Kayak | 340 | — | SocketCAN-Analyse-GUI |
| https://github.com/cedricp/ddt4all | 1909 | — | OBD/DiagBox-artiges Multi-Marken-Tool (ELM327) |
| https://github.com/brendan-w/python-OBD | 1324 | — | OBD-II-Python-Modul |
| https://github.com/rnd-ash/OpenVehicleDiag | 1020 | — | Rust-ECU-Diagnose (PassThru/J2534) |
| https://github.com/hexsecs/awesome-automotive-security | 24 | CC0 | Automotive-Security-Liste |

---

## I. Android / K-Line-Hardware-Bridge (für QFLASH21 & Co.)

| Repo | ★ | Inhalt |
|---|---|---|
| https://github.com/SchoepsLabs/webserial-android | 7 | Web Serial/WebUSB für Android-Geräte ohne Chrome ≥148 |
| https://github.com/selevo/WebUsbSerialTerminal | 16 | WebUSB-CH340-Terminal im Android-Browser |
| https://developer.chrome.com/docs/capabilities/serial | — | Web-Serial-Doku (USB-K-Line-Adapter: FTDI 0403:6001, CH340 1A86:7523, CP2102 10C4:EA60) |
| https://developer.mozilla.org/en-US/docs/Web/API/Serial_API | — | MDN-Kompatibilität (Chrome Android: 138 partiell/BT, 148 vollständig; WebView: nie) |

---

## J. Wissen & Foren

| Quelle | Inhalt |
|---|---|
| Bosch „EDC 15C Funktionsbeschreibung" B079.CC0 | via https://github.com/GabrielStanescu/BMW_M57_EDC15C4 (PDF) — Services, Fehlerspeicher-Aufbau (28-Byte-Einträge), EWS-Logik, 5-Baud-Init, McMess-Alternativprotokoll |
| https://ecuconnections.com | Tuning-Reverse-Engineering-Forum (EDC15-Threads, Prüfsummen-Diskussionen) |
| https://www.e90post.com/forums/showthread.php?t=1204192 | BMW Standard Tools 2.12-Setup-DIY (XP→Win10/11) |
| https://www.rangerovers.net/forums | L322-TD6-Community (ECU/Flash-Erfahrungen) |
| QFLASH21 `docs/EDC15C4-KI-AGENT.md` | https://github.com/batko15/QFLASH21 — Kalibrier-Referenz M57D30 (Stage-1-Ziel 230 PS/480 Nm, IQ-Limiter-Kette, Guardrails) |
| `docs/RESEARCH/github-findings.md` + `-2.md` (dieses Repo) | Unsere beiden Research-Runden: DTC-Struktur, EWS-Routine 0x83, DeepOBD-Format, Web-Serial-Fakten |

---

### Methodik & Verifizierung

- Jeder GitHub-Link oben wurde über `GET /repos/{owner}/{repo}` geprüft (404 sind ausgeschlossen; Stars/Lizenzen vom Katalogdatum).
- Recherche-Basis: 13+ API-Such-Queries (`EDC15C4`, `EDC15 checksum`, `EDC16/17`, `DDE4`, `KWP2000 flash`, `BMW INPA`, `udsoncan`, `damos/a2l`, …) + zwei vorherige Forschungsrunden (Task 7-a / 9-a).
- Bewusst **nicht** aufgenommen: Repos ohne verifizierbare Lizenz, die nur Marketing für kommerzielle Tools sind; Firmware-/Map-Sammlungen mit Lizenzproblemen (Bosch-PDF liegt im oben genannten öffentlichen Repo und wird nur verlinkt, nicht redistributet).
