# edc15-tools

Small, dependency-free Python tools for research on **Bosch EDC15** diesel ECUs
(Infineon/Siemens **C166** family), written while studying the ECU of my own
VW Bora 1.9 TDI.

| Tool | What it does |
|---|---|
| `edc15_checksum.py` | Verify and fix the EDC15 (tdi41v2 variant) checksum blocks of a 512 KB flash image from the command line |
| `c166_dis.py` | Minimal C166 disassembler for reading code regions of a flash dump |
| `kwp1281_probe.py` | KWP1281 over a plain K-line cable on a COM port: 5-baud init, ID blocks, measuring groups, read requests, cable echo test |

Code comments and CLI output are in Portuguese.

## edc15_checksum.py

```bash
python edc15_checksum.py verify image.bin
python edc15_checksum.py fix    in.bin out.bin
```

This is a faithful Python port of `EDC15P_checksum.cs` from
[VAGEDCSuite](https://github.com/skaldamramra/VAGEDCSuite) (GPL-3).

One detail is easy to get wrong when porting it. In the C# code the seeds are passed
**by value**, so the calculation never propagates them back. In practice the first
non-empty region uses seeds `(0, 0)` and every later region uses `(0x8631, 0xEFCD)`.
Regions filled with `0xC3` are treated as empty, and a stored `0xC3C3C3C3` is a
"skip" marker that is left untouched.

The checksum regions are bounded by
`0x10000, 0x14000, 0x58000, 0x58B80, 0x64000, 0x70000, 0x70B80, 0x7C000`, and each
region stores its 32-bit little-endian sum in its last 4 bytes.

## c166_dis.py

```bash
python c166_dis.py image.bin 5A000 5A200
```

File offset `x` maps to CPU address `0x80000 + x`. The tool covers the arithmetic and
logic groups, moves, jumps and calls, bit operations and common SFR names, which is
enough to follow most calibration-lookup code. For deeper work, use Ghidra with a
C166 processor module.

## kwp1281_probe.py

```bash
pip install pyserial
python kwp1281_probe.py --list
python kwp1281_probe.py --port COM4 --echo-test     # is this cable usable? (no ECU needed)
python kwp1281_probe.py --port COM4                 # init + identification
python kwp1281_probe.py --port COM4 --group 1       # measuring group
```

It needs a "dumb" K-line interface with raw access, such as an FTDI-based KKL cable or a
Ross-Tech interface running the VCP driver. Interfaces with a microcontroller between
the USB chip and the K-line (they return no echo) won't work. The default inter-byte
pause (`W4`) is 5 ms, which on a real ECU gave about 50 B/s with no failures.

## Scope

These tools are for research and diagnostics on vehicles you own or are authorised to
work on. They don't bypass immobilisers or security access. This repository contains
no Bosch firmware or calibration data.

## License

GPL-3.0, because the checksum code derives from VAGEDCSuite.
