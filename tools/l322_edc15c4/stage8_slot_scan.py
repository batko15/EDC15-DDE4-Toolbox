import struct, sys
sys.path.insert(0, "/home/z/my-project/work/refs/EDC15M-Checksum-Corrector")
UP = "/home/z/my-project/upload/"
A = open(UP+"L322 ORGINAL ECU FUL ALTES STEUERGERATL.bin","rb").read()
K = open(UP+"WinOLS_Land_Rover_Range_Rover_KENAN_TD6_ORIGINAL_große_Sensoren.bin","rb").read()
ori777 = open("/home/z/my-project/work/refs/BMW-DDE4-EDC15c4-EcuID/Original files/351777_ori.bin","rb").read()
ori618 = open("/home/z/my-project/work/refs/BMW-DDE4-EDC15c4-EcuID/Original files/361814_ori.bin","rb").read()

for name, d in (("A", A), ("K", K), ("351777", ori777), ("361814", ori618)):
    for base in (0x70000, 0x78000):
        idb = d[base+0xB7A:base+0xB7C]
        hits = []
        for slot in range(base+0x7000, base+0x8000+1, 0x80):
            if slot+4 <= len(d) and d[slot-6:slot-4] == idb and idb != b"\x00\x00":
                val = struct.unpack('<I', d[slot-4:slot])[0]
                if val not in (0xFFFFFFFF, 0x00000000, 0xC3C3C3C3):
                    hits.append((hex(slot), f"{val:08X}"))
        print(f"{name} base {base:05X}: ID={idb.hex()}  slot-hits: {hits}")

# also: what IS at 0x7EB52/0x7EB72 (the 0x0B80 occurrences in the tail)?
print("\nA[0x7EB40:0x7EB90]:", A[0x7EB40:0x7EB90].hex(' '))
