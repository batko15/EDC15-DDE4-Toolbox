#!/usr/bin/env python3
"""KWP1281 a partir do PC, por cabo K-line burro numa porta COM.

Validado no Bora (038906019CJ) com o cabo VCDS/HEX em modo VCP -- o driver
"Virtual COM-Port Driver for Ross-Tech USB Interfaces" transforma a interface
num FTDI normal com acesso cru a linha K.

    --echo-test    decide se o cabo serve, sem precisar da ECU nem da ignicao
    (sem flags)    init 5 baud + le os blocos de identificacao
    --read-ram     pede ReadRAM (title 3); so responde com o flash dos 2 NOPs

Nem todo o FTDI com porta COM serve: o VAG CAN PRO tem um MCU entre o FT232 e a
linha K e nunca devolve eco.
"""
import argparse
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("falta o pyserial:  python -m pip install pyserial")

BIT_TIME = 0.200        # 5 baud = 200 ms por bit
BAUD = 9600             # KWP1281 na familia EDC15 (10400 e KWP2000/ISO14230)
W4 = 0.005              # pausa antes do complemento. O max sao 50 ms; 30 era
                        # prudencia a mais e custava metade do debito. Medido
                        # no carro: 5 ms -> ~50 B/s em regime, 0 falhas.
BYTE_TIMEOUT = 1.0      # desistir se nao vier nada

TITLES = {0x00: "no-op", 0x03: "ReadRAM req", 0x06: "fim de sessao",
          0x09: "ACK", 0x0A: "NAK / recusa", 0x29: "req grupo", 0xF6: "ASCII",
          0xE7: "grupo resp", 0xFD: "ReadRAM resp", 0xFE: "ROM/EEPROM resp"}


def hexb(b):
    return f"{b:02X}"


class Aborted(Exception):
    pass


class Kwp:
    def __init__(self, port, verbose=True, dtr=True, rts=False, baud=BAUD, w4=W4,
                 reset_rx=True):
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baud
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.timeout = BYTE_TIMEOUT
        self.ser.write_timeout = 1.0
        self.ser.dsrdtr = False
        self.ser.rtscts = False
        self.ser.open()
        self.ser.dtr = dtr
        self.ser.rts = rts
        self.verbose = verbose
        self.w4 = w4            # pausa antes do complemento (o max e' 50 ms)
        # Limpar o buffer RX antes de cada byte custa um pedido USB, mas e'
        # obrigatorio: medido no carro, sem isto o protocolo parte de imediato.
        # Nao voltar a tentar.
        self.reset_rx = reset_rx
        self.echo_seen = False
        self.echo_checked = False
        self.counter = 0
        self.t0 = time.perf_counter()

    def log(self, msg):
        if self.verbose:
            print(f"[{time.perf_counter() - self.t0:7.3f}] {msg}")

    def close(self):
        try:
            self.ser.break_condition = False
        except Exception:
            pass
        self.ser.close()

    # ---------- camada de bytes ----------

    def _read(self, n=1):
        data = self.ser.read(n)
        if len(data) < n:
            raise Aborted(f"timeout a espera de {n} byte(s) (vieram {len(data)})")
        return data

    def read_byte(self, what=""):
        b = self._read(1)[0]
        self.log(f"  RX {hexb(b)}   {what}")
        return b

    def write_byte(self, b, what=""):
        """Escreve e consome o eco da propria linha K."""
        if self.reset_rx:
            self.ser.reset_input_buffer()
        self.ser.write(bytes([b]))
        self.ser.flush()
        self.log(f"  TX {hexb(b)}   {what}")
        echo = self.ser.read(1)
        if not self.echo_checked:
            self.echo_checked = True
            self.echo_seen = bool(echo) and echo[0] == b
            self.log("  >>> ECO da linha K detetado (cabo burro)" if self.echo_seen
                     else f"  >>> SEM eco (recebido: {hexb(echo[0]) if echo else 'nada'})")
        elif echo and echo[0] != b:
            return echo[0]      # nao era eco -- e um byte do parceiro
        return None

    def send_byte_acked(self, b, what=""):
        stray = self.write_byte(b, what)
        ack = stray if stray is not None else self.read_byte("(complemento)")
        want = (~b) & 0xFF
        if ack != want:
            raise Aborted(f"complemento errado: esperado {hexb(want)}, veio {hexb(ack)}")

    def recv_byte_acked(self, what=""):
        b = self.read_byte(what)
        time.sleep(self.w4)
        self.write_byte((~b) & 0xFF, "(complemento)")
        return b

    # ---------- init 5 baud ----------

    def slow_init(self, addr):
        """Bit-bang do endereco: start, 7 bits LSB-first, paridade impar, stop."""
        bits = [0]
        ones = 0
        for i in range(7):
            bit = (addr >> i) & 1
            bits.append(bit)
            ones += bit
        bits.append(0 if ones % 2 else 1)   # paridade impar
        bits.append(1)                      # stop

        self.log(f"slow init addr {hexb(addr)}  bits={''.join(str(b) for b in bits)}")
        self.ser.break_condition = False
        time.sleep(0.500)                   # W5: >= 300 ms de linha em repouso
        self.ser.reset_input_buffer()
        start = time.perf_counter()
        for i, bit in enumerate(bits):
            self.ser.break_condition = (bit == 0)   # break = linha a 0
            target = start + (i + 1) * BIT_TIME
            while time.perf_counter() < target:
                time.sleep(0.002)
        self.ser.break_condition = False
        during = self.ser.read(self.ser.in_waiting or 0)
        if during:
            self.log(f"  (lixo durante o init: {during.hex(' ').upper()} -- normal com eco)")

    def handshake(self, addr):
        self.slow_init(addr)
        deadline = time.perf_counter() + 1.5
        while time.perf_counter() < deadline:
            b = self.ser.read(1)
            if not b:
                continue
            if b[0] == 0x55:
                self.log("  RX 55   (sync)")
                break
            self.log(f"  RX {hexb(b[0])}   (a espera do 55, ignorado)")
        else:
            raise Aborted("nunca veio o byte de sincronismo 0x55")

        kw1 = self.read_byte("(KW1)")
        kw2 = self.read_byte("(KW2)")
        self.log(f"  keywords: {hexb(kw1)} {hexb(kw2)}"
                 f"{'  -> KWP1281' if (kw1, kw2) == (0x01, 0x8A) else ''}")
        time.sleep(self.w4)
        self.write_byte((~kw2) & 0xFF, "(complemento do KW2)")
        return kw1, kw2

    # ---------- camada de blocos ----------

    def recv_block(self):
        length = self.recv_byte_acked("(len)")
        body = [self.recv_byte_acked() for _ in range(length - 1)]
        etx = self.read_byte("(ETX)")
        if etx != 0x03:
            raise Aborted(f"fim de bloco errado: {hexb(etx)}")
        self.counter = body[0]
        return body[0], body[1], bytes(body[2:])

    def send_block(self, title, data=b""):
        """Manda um bloco com o contador seguinte ao ultimo recebido."""
        self.counter = (self.counter + 1) & 0xFF
        body = [self.counter, title] + list(data) + [0x03]
        seq = [len(body)] + body
        time.sleep(self.w4)
        for i, b in enumerate(seq):
            if i == len(seq) - 1:
                self.write_byte(b, "(ETX)")
            else:
                self.send_byte_acked(b)


def describe(title, data):
    label = TITLES.get(title, "?")
    out = f"title {hexb(title)} ({label})"
    if data:
        out += f"  {data.hex(' ').upper()}"
    if title == 0xF6:
        out += f"  ascii=\"{data.decode('latin-1', 'replace').strip()}\""
    return out


def echo_test(port, baud):
    """A linha K e um fio unico bidirecional: num cabo burro, tudo o que sai volta ao RX.

    Nao precisa da ECU nem da ignicao -- so de 12 V no pino 16 do OBD.
    """
    probe = bytes([0x55, 0xAA, 0x0F, 0xF0])
    print(f"=== teste de eco em {port} @ {baud} baud ===")
    print(f"    enviado sempre: {probe.hex(' ').upper()}\n")
    any_echo = False
    for dtr, rts in [(True, False), (False, False), (False, True), (True, True)]:
        s = serial.Serial()
        s.port, s.baudrate, s.timeout = port, baud, 0.4
        s.dsrdtr = s.rtscts = False
        try:
            s.open()
        except serial.SerialException as e:
            print(f"  nao abriu: {e}")
            return
        s.dtr, s.rts = dtr, rts
        time.sleep(0.15)
        s.reset_input_buffer()
        s.write(probe)
        s.flush()
        got = s.read(len(probe))
        s.close()
        if got == probe:
            verdict, any_echo = "ECO IGUAL  <<< cabo burro", True
        elif got:
            verdict = "algo voltou, mas diferente"
        else:
            verdict = "nada"
        print(f"  DTR={int(dtr)} RTS={int(rts)} -> {got.hex(' ').upper() or '(nada)':<12} [{verdict}]")
    if any_echo:
        print("\n  Ha acesso cru a linha K -> da para falar KWP1281 daqui.")
    else:
        print("\n  Sem eco em nenhuma combinacao: ou nao ha 12 V no pino 16 do OBD,"
              "\n  ou ha um MCU entre o FT232 e a linha K (interface 'inteligente').")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--addr", default="01", help="endereco do modulo em hex (01 = motor)")
    ap.add_argument("--baud", type=int, default=BAUD, help="9600 = KWP1281; 10400 = KWP2000")
    ap.add_argument("--blocks", type=int, default=12, help="quantos blocos de ident ler")
    ap.add_argument("--read-ram", metavar="HEX",
                    help="endereco de RAM a ler, ex: E01C (pedal). Precisa do unlock.")
    ap.add_argument("--count", type=int, default=4, help="quantos bytes ler")
    ap.add_argument("--group", type=int, metavar="N",
                    help="CONTROLO: pede o grupo de medida N (title 29). "
                         "Servico de serie -- se isto responde, a sessao esta boa.")
    ap.add_argument("--w4-ms", type=float, default=W4 * 1000,
                    help="pausa antes do complemento, em ms (max 50; menor = mais rapido)")
    ap.add_argument("--no-dtr", action="store_true")
    ap.add_argument("--rts", action="store_true")
    ap.add_argument("--no-reset-rx", action="store_true",
                    help="nao limpa o buffer de recepcao entre blocos")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dump", metavar="INI,FIM",
                    help="le um intervalo de offsets em hex e grava em --out")
    ap.add_argument("--out", default="dump.bin", help="ficheiro de saida do --dump")
    ap.add_argument("--read1", metavar="HEX,HEX,...",
                    help="title 1 (leitura por modo); offsets a partir da base da entrada")
    ap.add_argument("--watch", metavar="HEX,HEX,...",
                    help="le os mesmos enderecos varias vezes e marca o que muda")
    ap.add_argument("--iters", type=int, default=10, help="quantas leituras no --watch")
    ap.add_argument("--scan-addrs", metavar="HEX,HEX,...",
                    help="lista de enderecos para o varrimento (default: varredura grossa)")
    ap.add_argument("--scan-ram", action="store_true",
                    help="varre enderecos para descobrir a janela permitida do ReadRAM")
    ap.add_argument("--echo-test", action="store_true",
                    help="so testa se a linha K devolve eco (nao precisa da ECU)")
    args = ap.parse_args()

    if args.list:
        for p in list_ports.comports():
            print(f"{p.device:8} {p.description}  [{p.hwid}]")
        return 0

    if args.echo_test:
        echo_test(args.port, args.baud)
        return 0

    addr = int(args.addr, 16)
    print(f"=== KWP1281 em {args.port} @ {args.baud} baud, modulo {hexb(addr)} ===")
    k = Kwp(args.port, dtr=not args.no_dtr, rts=args.rts, baud=args.baud,
            w4=args.w4_ms / 1000.0, reset_rx=not args.no_reset_rx)
    ident, ram, grupo, scan = [], None, None, []
    try:
        k.handshake(addr)

        # a ECU cospe a identificacao e fecha com um ACK
        for _ in range(args.blocks):
            counter, title, data = k.recv_block()
            print(f"  <== bloco #{counter}: {describe(title, data)}")
            if title == 0xF6:
                ident.append(data.decode("latin-1", "replace").strip())
            k.send_block(0x09)
            if title == 0x09:
                break

        if args.group is not None:
            print(f"\n--- CONTROLO: grupo de medida {args.group} (title 29) ---")
            counter, title, data = k.recv_block()      # ACK da ECU
            print(f"  <== bloco #{counter}: {describe(title, data)}")
            k.send_block(0x29, bytes([args.group]))
            counter, title, data = k.recv_block()
            print(f"  <== bloco #{counter}: {describe(title, data)}")
            grupo = (title, data)

        if args.dump:
            ini, fim = [int(x, 16) for x in args.dump.split(',')]
            passo = args.count
            print(f"\n--- dump 0x{ini:04X}-0x{fim:04X} ({fim - ini} bytes, {passo} por bloco) ---")
            k.verbose = False
            counter, title, data = k.recv_block()      # ACK da ECU
            buf = bytearray()
            falhas = 0
            for a in range(ini, fim, passo):
                n = min(passo, fim - a)
                k.send_block(0x03, bytes([n, (a >> 8) & 0xFF, a & 0xFF]))
                counter, title, data = k.recv_block()
                if title == 0xFD and len(data) == n:
                    buf += data
                else:
                    buf += b'\x00' * n
                    falhas += 1
                k.send_block(0x09)
                counter, title, data = k.recv_block()
            k.verbose = True
            k.send_block(0x06)
            with open(args.out, 'wb') as f:
                f.write(buf)
            print(f"  {len(buf)} bytes -> {args.out}   ({falhas} bloco(s) falhado(s))")

        if args.read1 is not None:
            # title 1 = "leitura por modo". O modo (0xCE88) escolhe a entrada da tabela
            # de janelas; entradas 1 e 2 tem pagina 0x03 -> base 0x0C000 (RAM).
            alvos = [int(x, 16) for x in args.read1.split(',')]
            print(f"\n--- title 1 (leitura por modo): {len(alvos)} offset(s) ---")
            k.verbose = False
            counter, title, data = k.recv_block()      # ACK da ECU
            for alvo in alvos:
                k.send_block(0x01, bytes([args.count, (alvo >> 8) & 0xFF, alvo & 0xFF]))
                counter, title, data = k.recv_block()
                nome = TITLES.get(title, '?')
                print(f"  offset 0x{alvo:04X} -> title {hexb(title)} ({nome})"
                      + (f"  {data.hex(' ').upper()}" if data else ""))
                k.send_block(0x09)
                counter, title, data = k.recv_block()
            k.verbose = True
            k.send_block(0x06)

        if args.watch:
            alvos = [int(x, 16) for x in args.watch.split(',')]
            print(f"\n--- watch: {len(alvos)} endereco(s), {args.iters} leituras ---")
            print("  (carrega nos pedais durante a leitura; '*' marca o que mudou)")
            k.verbose = False
            counter, title, data = k.recv_block()      # ACK da ECU
            anterior = {}
            for it in range(args.iters):
                linha = []
                for alvo in alvos:
                    k.send_block(0x03, bytes([args.count, (alvo >> 8) & 0xFF, alvo & 0xFF]))
                    counter, title, data = k.recv_block()
                    val = data.hex(' ').upper() if title == 0xFD else f"!{hexb(title)}"
                    mudou = alvo in anterior and anterior[alvo] != val
                    anterior[alvo] = val
                    linha.append(f"{alvo:04X}={val}{'*' if mudou else ' '}")
                    k.send_block(0x09)
                    counter, title, data = k.recv_block()
                print(f"  [{it:2}] " + "  ".join(linha))
            k.verbose = True
            k.send_block(0x06)

        if args.scan_ram:
            # o emissor 0xA35A0 valida endereco+count contra uma janela por servico;
            # varrer revela a janela sem flashar nada
            if args.scan_addrs:
                alvos = [int(x, 16) for x in args.scan_addrs.split(',')]
            else:
                alvos = [0x0000, 0x1000, 0x2000, 0x4000, 0x8000, 0xA000, 0xC000, 0xC096,
                         0xC76E, 0xCD72, 0xD000, 0xE000, 0xE01C, 0xE798, 0xF000, 0xFB00]
            print(f"\n--- varrimento de janela: {len(alvos)} enderecos, count=1 ---")
            k.verbose = False
            counter, title, data = k.recv_block()      # ACK da ECU
            for alvo in alvos:
                k.send_block(0x03, bytes([1, (alvo >> 8) & 0xFF, alvo & 0xFF]))
                counter, title, data = k.recv_block()
                marca = "FD  <<< PASSOU" if title == 0xFD else f"{hexb(title)}"
                print(f"  0x{alvo:04X} -> {marca}"
                      + (f"  dados={data.hex(' ').upper()}" if title == 0xFD else ""))
                scan.append((alvo, title, data))
                k.send_block(0x09)                      # ACK
                counter, title, data = k.recv_block()   # ACK da ECU
            k.verbose = True
            k.send_block(0x06)

        if args.read_ram is not None:
            target = int(args.read_ram, 16)
            print(f"\n--- ReadRAM: {args.count} byte(s) em 0x{target:04X} ---")
            counter, title, data = k.recv_block()      # ACK da ECU
            print(f"  <== bloco #{counter}: {describe(title, data)}")
            payload = bytes([args.count, (target >> 8) & 0xFF, target & 0xFF])
            k.send_block(0x03, payload)
            counter, title, data = k.recv_block()
            print(f"  <== bloco #{counter}: {describe(title, data)}")
            ram = (title, data)
            k.send_block(0x06)                          # fechar sessao
    except Aborted as e:
        print(f"\n!! parou: {e}")
    except KeyboardInterrupt:
        print("\n!! interrompido")
    finally:
        k.close()

    print("\n=== VEREDICTO ===")
    if not k.echo_checked:
        print("  nao chegou a transmitir nada -- inconclusivo")
    elif k.echo_seen:
        print("  ECO PRESENTE -> cabo burro, acesso cru a linha K.")
    else:
        print("  SEM ECO -> ou nao ha 12 V do OBD, ou ha um MCU pelo meio.")
    if ident:
        print("  identificacao da ECU: " + " | ".join(x for x in ident if x))
    if grupo:
        title, data = grupo
        if title == 0xE7:
            print(f"  CONTROLO OK -> a ECU aceita pedidos nossos (grupo respondeu {data.hex(' ').upper()})")
        else:
            print(f"  CONTROLO FALHOU -> title {hexb(title)} ({TITLES.get(title, '?')}) tambem."
                  "\n  Entao o problema nao e' o unlock: e' a nossa sessao/enquadramento.")
    if ram:
        title, data = ram
        if title == 0xFD:
            print(f"  ReadRAM ABERTO -> {data.hex(' ').upper()}")
        else:
            print(f"  ReadRAM RECUSADO -> respondeu title {hexb(title)} "
                  f"({TITLES.get(title, '?')}) em vez de FD."
                  "\n  Esperado sem os 2 NOPs do unlock no flash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
