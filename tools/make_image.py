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
import os
import struct
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from zlib import crc32


HEADER_FIXED_SIZE = 16
CONFIG_WORD_SIZE = 8
CHECKSUM_SIZE = 1
CRC_SIZE = 4
TRAILER_SIZE = CHECKSUM_SIZE + CRC_SIZE

FW_VERSION_OFFSET = 0x80
FW_MAGIC_OFFSET = 0x87
SIGNATURE_SIZE = 0x20

BODY_LEN_FORMATS = {2: "H", 4: "I"}

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


@dataclass(frozen=True)
class ChipInfo:
    name: str
    header_magic: bytes
    body_magic: bytes
    body_len_width: int  # Width in bytes of the body length field.
    config_offset: int  # Offset at which the ROM starts reading config words.
    has_signature: bool = False
    supports_sig_bypass: bool = False


CHIP_INFO: dict[str, ChipInfo] = {
    "ASM1042": ChipInfo("ASM1042", b"U2104_RCFG", b"U2104_FW", 2, 0x10),
    "ASM1042A": ChipInfo("ASM1042A", b"2104B_RCFG", b"2104B_FW", 2, 0x10),
    "ASM1142": ChipInfo("ASM1142", b"2114A_RCFG", b"2114A_FW", 2, 0x10),
    "ASM2142": ChipInfo("ASM2142", b"2214A_RCFG", b"2214A_FW", 4, 0x20),
    "ASM3242": ChipInfo(
        "ASM3242", b"2324A_RCFG", b"2324A_FW", 4, 0x20,
        has_signature=True, supports_sig_bypass=True,
    ),
}


class FirmwareBuildError(Exception):
    pass


def checksum(data: bytes) -> int:
    return sum(data) & 0xff

def trailer(data: bytes) -> bytes:
    return struct.pack('<BI', checksum(data), crc32(data))

def encode_mmio_write(addr: int, size: int, value: int) -> bytes:
    return struct.pack('<BBHI', CONFIG_WORD_TYPE_WRITE, size, addr, value)

def build_bypass_sequence(chip_info: ChipInfo, firmware_size: int) -> bytes:
    if firmware_size > BYPASS_READ_LEN:
        raise FirmwareBuildError(
            "{} firmware is too large for the signature check bypass: "
            "{} bytes (maximum is {})".format(
                chip_info.name, firmware_size, BYPASS_READ_LEN
            )
        )

    # Bypass the signature check via ROM config MMIO writes.
    xram_addr = 0x000000  # Always zero.
    data_len = BYPASS_READ_LEN  # Limited by the flash read speed.

    config_len = chip_info.config_offset - HEADER_FIXED_SIZE

    cc_words = 14
    delay_writes = (
        BYPASS_HEADER_SIZE
        - (HEADER_FIXED_SIZE + config_len + CONFIG_WORD_SIZE * cc_words)
    ) // CONFIG_WORD_SIZE
    if delay_writes < len(BYPASS_LOADING_STRING):
        raise FirmwareBuildError(
            "not enough room in the {} image header for the loading message".format(
                chip_info.name
            )
        )

    header_len = HEADER_FIXED_SIZE + config_len + CONFIG_WORD_SIZE * (cc_words + delay_writes)
    if header_len != BYPASS_HEADER_SIZE:
        raise FirmwareBuildError(
            "cannot pad the {} image header to {} bytes".format(
                chip_info.name, BYPASS_HEADER_SIZE
            )
        )

    firmware_flash_addr = (
        HEADER_FIXED_SIZE
        + config_len
        + CONFIG_WORD_SIZE * (cc_words + delay_writes)
        + TRAILER_SIZE
        + chip_info.body_len_width
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

    data = bytes()
    for addr, count, value in writes_pre_delay:
        data += encode_mmio_write(addr, count, value)
    for char in loading_string:
        data += encode_mmio_write(BYPASS_LOADING_ADDR, 4, char << 8)
    for addr, count, value in writes_post_delay:
        data += encode_mmio_write(addr, count, value)

    return data

def build_header(chip_info: ChipInfo, firmware_size: int, sig_bypass: bool = False) -> bytes:
    if sig_bypass and not chip_info.supports_sig_bypass:
        raise FirmwareBuildError(
            "{} does not support the signature check bypass".format(chip_info.name)
        )

    data = bytes()
    # The mask ROM starts reading config words at 0x10 on older chips and at
    # 0x20 on ASM2142 and later.
    data += bytes(chip_info.config_offset - HEADER_FIXED_SIZE)

    if chip_info.supports_sig_bypass and sig_bypass:
        data += build_bypass_sequence(chip_info, firmware_size)

    header = struct.pack(
        '<HHH10s', 0, 1, HEADER_FIXED_SIZE + len(data), chip_info.header_magic
    )
    header += data

    header += trailer(header)

    return header

def build_body(chip_info: ChipInfo, firmware: bytes) -> bytes:
    if not firmware:
        raise FirmwareBuildError("{} firmware is empty".format(chip_info.name))

    max_len = (1 << (8 * chip_info.body_len_width)) - 1
    if len(firmware) > max_len:
        raise FirmwareBuildError(
            "{} firmware is too large: {} bytes (maximum is {})".format(
                chip_info.name, len(firmware), max_len
            )
        )

    body = struct.pack('<' + BODY_LEN_FORMATS[chip_info.body_len_width], len(firmware))
    body += firmware
    body += struct.pack('8s', chip_info.body_magic)

    body += trailer(firmware)

    if chip_info.has_signature:
        # Append a null signature to enable the Kaitai Struct definition and
        # firmware validation script to work on custom ASM3242 firmware
        # images.
        body += struct.pack('BBB', 0, 3 << 1, 0x00 >> 2)
        body += bytes(SIGNATURE_SIZE)

    return body

def build_image(chip_info: ChipInfo, firmware: bytes, sig_bypass: bool = False) -> bytes:
    return build_header(chip_info, len(firmware), sig_bypass) + build_body(chip_info, firmware)

def add_fw_meta(chip_info: ChipInfo, data: bytes) -> bytes:
    required_len = FW_MAGIC_OFFSET + len(chip_info.body_magic)
    if len(data) < required_len:
        raise FirmwareBuildError(
            "{} firmware is too small: {} bytes (minimum is {})".format(
                chip_info.name, len(data), required_len
            )
        )

    data = bytearray(data)
    bcd_timestamp = bytes.fromhex(datetime.utcnow().strftime('%y%m%d%H%M%S'))
    struct.pack_into('6s', data, FW_VERSION_OFFSET, bcd_timestamp)
    struct.pack_into('8s', data, FW_MAGIC_OFFSET, chip_info.body_magic)

    return bytes(data)

def write_output(path: str, data: bytes) -> None:
    # Write to a temporary file in the destination directory and rename it, so
    # an interrupted or failed build cannot leave a truncated image behind.
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)

        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp_path, 0o666 & ~umask)

        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input binary.")
    parser.add_argument("-t", "--type", type=str, choices=["bin", "image"], default="image", help="Image type.")
    parser.add_argument("-o", "--output", type=str, default="monitor.img", help="Output image.")
    parser.add_argument("-c", "--chip", type=str, choices=CHIP_INFO.keys(), default="ASM1142", help="Chip to target.")
    parser.add_argument("-s", "--sig-bypass", default=False, action="store_true", help="Add MMIO writes in the image header to bypass the signature check, when applicable.")
    args = parser.parse_args(argv)

    try:
        with open(args.input, 'rb') as input_file:
            binary = input_file.read()

        chip_info = CHIP_INFO[args.chip]

        if args.sig_bypass and args.type == "bin":
            raise FirmwareBuildError("the signature check bypass only applies to images")

        if args.type == "bin":
            image = add_fw_meta(chip_info, binary)
        elif args.type == "image":
            image = build_image(chip_info, binary, args.sig_bypass)
        else:
            print("Error: Unrecognized image type: {}".format(args.type))
            return 1

        write_output(args.output, image)
    except FirmwareBuildError as e:
        print("Error: {}".format(e), file=sys.stderr)
        return 1
    except OSError as e:
        print("Error: {}".format(e), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
