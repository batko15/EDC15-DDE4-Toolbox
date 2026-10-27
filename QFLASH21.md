# QFLASH21 — Schwesterprojekt

Die interaktive Seite der Werkzeugkette lebt im eigenen Repo:

**https://github.com/batko15/QFLASH21**

- DDE4 (EDC15C4)-Diagnose & Flash direkt im Browser (K-Line/KWP2000, Web Serial)
- 5-Baud-Init (SG-Adresse 0x12, Keywords 0x45 0x05), Ident, Fehlerspeicher normal + Schatten,
  51 EDC15-DTC-Texte (deutsch), 5 Messwertblöcke (LID 0x03/0x07/0x13/0x15/0x17),
  Steuergeräte-Jobs (0x11 Reset, 0x30 Aktuatorik, 0x31 Routinen), FULL-512K/CAL-48K-Lesen,
  CR2-Bankprüfsummen mit Korrektur, Schreib-Gate (Phrase + Spannung + Backup-Pflicht),
  Simulator für Betrieb ohne Fahrzeug, Android-APK (standalone, offline)
- Deployment: Vercel + Supabase (https://qflashk.vercel.app)
- Tuning-Wissen für M57D30: `docs/EDC15C4-KI-AGENT.md` im QFLASH21-Repo
