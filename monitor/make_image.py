#!/usr/bin/env python3

import argparse
import struct
import sys
from datetime import datetime
from zlib import crc32


CHIP_INFO = {
    "ASM1042": ("U2104_RCFG", "U2104_FW", "H"),
    "ASM1042A": ("2104B_RCFG", "2104B_FW", "H"),
    "ASM1142": ("2114A_RCFG", "2114A_FW", "H"),
    "ASM2142": ("2214A_RCFG", "2214A_FW", "I"),
    "ASM3242": ("2324A_RCFG", "2324A_FW", "I"),
}


def checksum(data : bytes):
    return sum(data) & 0xff

def gen_header(chip : str):
    header_magic = CHIP_INFO[chip][0]

    data = bytes()
    if CHIP_INFO[chip][2] == "I":
        # Config words start at 0x20 on ASM2142 and later.
        data += bytes([0] * 16)

    if chip == "ASM3242":
        # Bypass the signature check via ROM config MMIO writes.
        xram_addr = 0x000000  # Always zero.
        data_len = 0x008000  # Limited by the flash read speed.

        cc_words = 14
        delay_writes = (0x400 - (16 + len(data) + 8 * cc_words)) // 8
        firmware_flash_addr = 16 + len(data) + 8 * (cc_words + delay_writes) + 9

        writes_pre_delay = (
            (0x505c, 2, data_len & 0xffff),  # DATA_LEN
            (0x505e, 1, (data_len >> 16) & 0xff),  # DATA_LEN_HI
            (0x5060, 1, 0x01),  # DIV
            (0x5061, 1, 0x03),  # ADDR_LEN
            (0x5062, 1, 0x03),  # CMD
            (0x5063, 1, 0x00),  # MODE
            (0x5064, 1, 0x01),  # MEMSEL
            (0x5066, 2, xram_addr & 0xffff),  # XRAM_ADDR
            (0x5068, 1, (xram_addr >> 16) & 0xff),  # XRAM_ADDR_HI
            (0x506b, 2, firmware_flash_addr & 0xffff),  # FLASH_ADDR
            (0x506d, 1, (firmware_flash_addr >> 16) & 0xff),  # FLASH_ADDR_HI
            (0x506e, 1, 0x04 | 0x08 | 0x01),  # CSR
        )

        writes_post_delay = (
            (0x5040, 1, 0x03),  # CPU_MODE_NEXT
            (0x5042, 1, 0x01),  # CPU_EXEC_CTRL
        )

        loading_string = b"\r\nLoading..."
        loading_string += b"." * (delay_writes - len(loading_string))

        for addr, count, value in writes_pre_delay:
            data += struct.pack('<BBHI', 0xCC, count, addr, value)
        for char in loading_string:
            data += struct.pack('<BBHI', 0xCC, 4, 0x5100, char << 8)
        for addr, count, value in writes_post_delay:
            data += struct.pack('<BBHI', 0xCC, count, addr, value)

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

    body = struct.pack('<' + body_len_type, len(data))
    body += data
    body += struct.pack('8s', body_magic)

    csum = checksum(data)
    crc = crc32(data)
    body += struct.pack('<BI', csum, crc)

    if body_magic == b"2324A_FW":
        # Append a null signature to enable the Kaitai Struct definition and
        # firmware validation script to work on custom ASM3242 firmware
        # images.
        body += struct.pack('BBB', 0, 3 << 1, 0x00 >> 2)
        body += bytes([0] * 0x20)

    return body

def add_fw_meta(chip : str, data : bytes):
    chip_info = CHIP_INFO[chip]
    body_magic = chip_info[1].encode('ASCII')

    data = bytearray(data)
    bcd_timestamp = bytes.fromhex(datetime.utcnow().strftime('%y%m%d%H%M%S'))
    struct.pack_into('6s', data, 0x80, bcd_timestamp)
    struct.pack_into('8s', data, 0x87, body_magic)

    return bytes(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input binary.")
    parser.add_argument("-t", "--type", type=str, choices=["bin", "image"], default="image", help="Image type.")
    parser.add_argument("-o", "--output", type=str, default="monitor.img", help="Output image.")
    parser.add_argument("-c", "--chip", type=str, choices=CHIP_INFO.keys(), default="ASM1142", help="Chip to target.")
    args = parser.parse_args()

    binary = open(args.input, 'rb').read()

    if args.type == "bin":
        image = add_fw_meta(args.chip, binary)
    elif args.type == "image":
        header = gen_header(args.chip)
        body = gen_body(args.chip, binary)
        image = header + body
    else:
        print("Error: Unrecognized image type: {}".format(args.type))
        return 1

    output = open(args.output, 'wb')
    output.write(image)
    output.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
