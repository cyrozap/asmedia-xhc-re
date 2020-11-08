#!/usr/bin/env python3

import argparse
import struct
import sys
from datetime import datetime
from zlib import crc32


CHIP_INFO = {
    "ASM1042": ("U2104_RCFG", "U2104_FW", "H"),
    "ASM1142": ("2114A_RCFG", "2114A_FW", "H"),
    "ASM2142": ("2214A_RCFG", "2214A_FW", "I"),
}


def checksum(data : bytes):
    return sum(data) & 0xff

def gen_header(chip : str):
    header_magic = CHIP_INFO[chip][0]

    data = bytes()

    header = struct.pack('<HHH10s', 0, 1, 16 + len(data), header_magic.encode('ASCII'))
    header += data

    csum = checksum(header)
    crc = crc32(header)
    header += struct.pack('<BI', csum, crc)

    return header

def gen_body(chip : str, data : bytes):
    chip_info = CHIP_INFO[chip]
    body_magic = chip_info[1].encode('ASCII')
    body_len_type = chip_info[2]

    data = bytearray(data)
    bcd_timestamp = bytes.fromhex(datetime.utcnow().strftime('%y%m%d%H%M%S'))
    struct.pack_into('6s', data, 0x80, bcd_timestamp)
    struct.pack_into('8s', data, 0x87, body_magic)

    body = struct.pack('<' + body_len_type, len(data))
    body += data
    body += struct.pack('8s', body_magic)

    csum = checksum(data)
    crc = crc32(data)
    body += struct.pack('<BI', csum, crc)

    return body

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input binary.")
    parser.add_argument("-o", "--output", type=str, default="monitor.img", help="Output image.")
    parser.add_argument("-c", "--chip", type=str, choices=CHIP_INFO.keys(), default="ASM1142", help="Chip to target.")
    args = parser.parse_args()

    binary = open(args.input, 'rb').read()

    header = gen_header(args.chip)
    body = gen_body(args.chip, binary)

    image = header + body
    image += (0x10000 - len(image)) * b'\0'

    output = open(args.output, 'wb')
    output.write(image)
    output.close()


if __name__ == "__main__":
        main()
