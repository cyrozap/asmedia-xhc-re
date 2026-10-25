#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# make_image.py - Script to generate a firmware image from a raw binary.
# Copyright (C) 2020-2023, 2025-2026  Forest Crossman <cyrozap@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import argparse
import struct
import sys
from datetime import datetime
from zlib import crc32


HEADER_FIXED_SIZE = 16
CONFIG_WORD_SIZE = 8
CONFIG_PAD_SIZE = 16
CHECKSUM_SIZE = 1
CRC_SIZE = 4
TRAILER_SIZE = CHECKSUM_SIZE + CRC_SIZE

FW_VERSION_OFFSET = 0x80
FW_MAGIC_OFFSET = 0x87
SIGNATURE_SIZE = 0x20

BYPASS_HEADER_SIZE = 0x400
BYPASS_READ_LEN = 0x008000
BYPASS_LOADING_ADDR = 0x5100
BYPASS_LOADING_STRING = b"\r\nLoading..."

CONFIG_WORD_TYPE_WRITE = 0xCC

FLASH_CON_DATA_LEN = 0x505c
FLASH_CON_DATA_LEN_HI = 0x505e
FLASH_CON_DIV = 0x5060
FLASH_CON_ADDR_LEN = 0x5061
FLASH_CON_JEDEC_CMD = 0x5062
FLASH_CON_MODE = 0x5063
FLASH_CON_MEMSEL = 0x5064
FLASH_CON_XRAM_ADDR = 0x5066
FLASH_CON_XRAM_ADDR_HI = 0x5068
FLASH_CON_FLASH_ADDR = 0x506b
FLASH_CON_FLASH_ADDR_HI = 0x506d
FLASH_CON_CSR = 0x506e

CPU_MODE_NEXT = 0x5040
CPU_EXEC_CTRL = 0x5042


CHIP_INFO = {
    "ASM1042": ("U2104_RCFG", "U2104_FW", "H"),
    "ASM1042A": ("2104B_RCFG", "2104B_FW", "H"),
    "ASM1142": ("2114A_RCFG", "2114A_FW", "H"),
    "ASM2142": ("2214A_RCFG", "2214A_FW", "I"),
    "ASM3242": ("2324A_RCFG", "2324A_FW", "I"),
}


def checksum(data: bytes) -> int:
    return sum(data) & 0xff

def gen_header(chip: str, sig_bypass: bool = False) -> bytes:
    header_magic = CHIP_INFO[chip][0]

    data = bytes()
    if CHIP_INFO[chip][2] == "I":
        # Config words start at 0x20 on ASM2142 and later.
        data += bytes([0] * CONFIG_PAD_SIZE)

    if chip == "ASM3242" and sig_bypass:
        # Bypass the signature check via ROM config MMIO writes.
        xram_addr = 0x000000  # Always zero.
        data_len = BYPASS_READ_LEN  # Limited by the flash read speed.

        cc_words = 14
        delay_writes = (
            BYPASS_HEADER_SIZE
            - (HEADER_FIXED_SIZE + len(data) + CONFIG_WORD_SIZE * cc_words)
        ) // CONFIG_WORD_SIZE
        firmware_flash_addr = (
            HEADER_FIXED_SIZE
            + len(data)
            + CONFIG_WORD_SIZE * (cc_words + delay_writes)
            + TRAILER_SIZE
            + struct.calcsize('<' + CHIP_INFO[chip][2])
        )

        writes_pre_delay = (
            (FLASH_CON_DATA_LEN, 2, data_len & 0xffff),
            (FLASH_CON_DATA_LEN_HI, 1, (data_len >> 16) & 0xff),
            (FLASH_CON_DIV, 1, 0x01),
            (FLASH_CON_ADDR_LEN, 1, 0x03),
            (FLASH_CON_JEDEC_CMD, 1, 0x03),
            (FLASH_CON_MODE, 1, 0x00),
            (FLASH_CON_MEMSEL, 1, 0x01),
            (FLASH_CON_XRAM_ADDR, 2, xram_addr & 0xffff),
            (FLASH_CON_XRAM_ADDR_HI, 1, (xram_addr >> 16) & 0xff),
            (FLASH_CON_FLASH_ADDR, 2, firmware_flash_addr & 0xffff),
            (FLASH_CON_FLASH_ADDR_HI, 1, (firmware_flash_addr >> 16) & 0xff),
            (FLASH_CON_CSR, 1, 0x04 | 0x08 | 0x01),
        )

        writes_post_delay = (
            (CPU_MODE_NEXT, 1, 0x03),
            (CPU_EXEC_CTRL, 1, 0x01),
        )

        loading_string = BYPASS_LOADING_STRING
        loading_string += b"." * (delay_writes - len(loading_string))

        for addr, count, value in writes_pre_delay:
            data += struct.pack('<BBHI', CONFIG_WORD_TYPE_WRITE, count, addr, value)
        for char in loading_string:
            data += struct.pack('<BBHI', CONFIG_WORD_TYPE_WRITE, 4, BYPASS_LOADING_ADDR, char << 8)
        for addr, count, value in writes_post_delay:
            data += struct.pack('<BBHI', CONFIG_WORD_TYPE_WRITE, count, addr, value)

    header = struct.pack('<HHH10s', 0, 1, HEADER_FIXED_SIZE + len(data), header_magic.encode('ASCII'))
    header += data

    csum = checksum(header)
    crc = crc32(header)
    header += struct.pack('<BI', csum, crc)

    return header

def gen_body(chip: str, data: bytes) -> bytes:
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
        body += bytes(SIGNATURE_SIZE)

    return body

def add_fw_meta(chip: str, data: bytes) -> bytes:
    chip_info = CHIP_INFO[chip]
    body_magic = chip_info[1].encode('ASCII')

    data = bytearray(data)
    bcd_timestamp = bytes.fromhex(datetime.utcnow().strftime('%y%m%d%H%M%S'))
    struct.pack_into('6s', data, FW_VERSION_OFFSET, bcd_timestamp)
    struct.pack_into('8s', data, FW_MAGIC_OFFSET, body_magic)

    return bytes(data)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input binary.")
    parser.add_argument("-t", "--type", type=str, choices=["bin", "image"], default="image", help="Image type.")
    parser.add_argument("-o", "--output", type=str, default="monitor.img", help="Output image.")
    parser.add_argument("-c", "--chip", type=str, choices=CHIP_INFO.keys(), default="ASM1142", help="Chip to target.")
    parser.add_argument("-s", "--sig-bypass", default=False, action="store_true", help="Add MMIO writes in the image header to bypass the signature check, when applicable.")
    args = parser.parse_args()

    binary = open(args.input, 'rb').read()

    if args.type == "bin":
        image = add_fw_meta(args.chip, binary)
    elif args.type == "image":
        header = gen_header(args.chip, args.sig_bypass)
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
