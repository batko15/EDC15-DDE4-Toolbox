#!/usr/bin/env python3
"""Checksums do EDC15 (variante tdi41v2) -- verificar e corrigir sem o VAGEDCSuite.

Porte fiel de EDC15P_checksum.cs (VAGEDCSuite, GPL-3): tdi41v2_checksum_search +
tdi41_checksum_calculate.

Pormenor que importa: em C# as seeds sao passadas POR VALOR, por isso o calculo
nao as propaga de volta. Resultado pratico -- a primeira regiao processada usa
(0,0) e todas as seguintes usam (0x8631, 0xEFCD).

Uso:
    edc15_checksum.py verify <ficheiro.bin>
    edc15_checksum.py fix    <entrada.bin> <saida.bin>
"""
import sys

CHK_ARRAY = [0x10000, 0x14000, 0x58000, 0x58B80, 0x64000, 0x70000, 0x70B80, 0x7C000]
SKIP = 0xC3C3C3C3
M16 = 0xFFFF


def w(d, i):
    return d[i] | (d[i + 1] << 8)


def calculate(d, start, end, seed_a, seed_b):
    p = start
    while True:
        var_2 = 0
        seed_a = (seed_a ^ w(d, p)) & M16
        p += 2
        n = seed_b & 0xF
        if n > 0:
            var_1 = seed_a >> (16 - n)
            seed_a = ((seed_a << n) & M16) | var_1
            var_2 = seed_a & 1
        seed_b = (seed_b - w(d, p)) & M16
        seed_b = (seed_b - var_2) & M16
        p += 2
        seed_b = (seed_b ^ seed_a) & M16
        if p == end:
            break
        seed_a = (seed_a - w(d, p)) & M16
        p += 2
        seed_a = (seed_a + 0xDAAC) & M16
        seed_b = (seed_b ^ w(d, p)) & M16
        p += 2
        n = seed_a & 0xF
        if n > 0:
            var_1 = (seed_b << (16 - n)) & M16
            seed_b = (seed_b >> n) | var_1
        if p == end:
            break

    seed_a = (seed_a - 0x8631) & M16
    seed_a = (seed_a + 0xDAAC) & M16
    seed_b = (seed_b ^ 0xDF9B) & M16
    return ((seed_b << 16) + seed_a) & 0xFFFFFFFF


def is_empty(d, start, end):
    return all(b == 0xC3 for b in d[start:end - 4])


def walk(d, apply_fix):
    """Percorre as regioes; devolve (linhas, n_corrigidos)."""
    seed_a = seed_b = 0
    first_pass = True
    linhas = []
    fixed_n = 0
    for i in range(len(CHK_ARRAY) - 1):
        start, end = CHK_ARRAY[i], CHK_ARRAY[i + 1]
        if not first_pass:
            seed_a |= 0x8631
            seed_b |= 0xEFCD
        if is_empty(d, start, end):
            linhas.append(f'  0x{start:05X}-0x{end:05X}  slot 0x{end - 4:05X}  vazia (0xC3)')
            continue
        old = int.from_bytes(d[end - 4:end], 'little')
        calc = calculate(d, start, end - 4, seed_a, seed_b)
        if old == SKIP:
            estado = 'C3skip (nao se toca)'
        elif old == calc:
            estado = 'match'
        else:
            estado = 'DIFERE'
            if apply_fix:
                d[end - 4:end] = calc.to_bytes(4, 'little')
                estado = f'CORRIGIDO -> {calc:08X}'
                fixed_n += 1
        linhas.append(f'  0x{start:05X}-0x{end:05X}  slot 0x{end - 4:05X}  '
                      f'ficheiro={old:08X} calc={calc:08X}  {estado}')
        first_pass = False
    return linhas, fixed_n


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    modo, caminho = sys.argv[1], sys.argv[2]
    d = bytearray(open(caminho, 'rb').read())
    if len(d) != 0x80000:
        raise SystemExit(f'ERRO: esperava 512 KB, tem {len(d)} bytes')

    linhas, n = walk(d, apply_fix=(modo == 'fix'))
    print(f'--- {caminho} ---')
    print('\n'.join(linhas))

    if modo == 'fix':
        if len(sys.argv) < 4:
            raise SystemExit('ERRO: falta o ficheiro de saida')
        open(sys.argv[3], 'wb').write(d)
        print(f'\n{n} slot(s) corrigido(s) -> {sys.argv[3]}')
        linhas2, _ = walk(bytearray(d), apply_fix=False)
        print('--- confirmacao ---')
        print('\n'.join(linhas2))
    else:
        mau = sum(1 for x in linhas if 'DIFERE' in x)
        print(f'\nok: {mau == 0}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
