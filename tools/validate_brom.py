#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# validate_brom.py - A tool to validate that a boot ROM was dumped properly.
# Copyright (C) 2021, 2024  Forest Crossman <cyrozap@gmail.com>
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
from zlib import crc32


CHIPS = {
    bytes(8): "ASM1042",
    b"2104B_FW": "ASM1042A",
    b"2114A_FW": "ASM1142",
    b"2214A_FW": "ASM2142/ASM3142",
    b"2324A_FW": "ASM3242",
    b"3328A_FW": "ASM3283/Prom21",
}


def validate_crc32(data, expected):
    calc_crc32 = crc32(data)
    exp_crc32 = expected
    if calc_crc32 != exp_crc32:
        raise ValueError("Invalid CRC-32: expected {:#010x}, got: {:#010x}".format(exp_crc32, calc_crc32))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=str, help="The ASMedia USB 3 host controller boot ROM binary.")
    args = parser.parse_args()

    fw_bytes = open(args.firmware, 'rb').read()
    chip_magic = fw_bytes[0x87:0x87+8]
    chip_name = CHIPS.get(chip_magic, "Unknown magic: {}".format(chip_magic))

    for size in (0x8000, 0x10000):
        expected = struct.unpack_from('<I', fw_bytes, size-4)[0]

        try:
            validate_crc32(fw_bytes[:size-4], expected)

            version_bytes = fw_bytes[0x80:0x80+6]
            version_string = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*version_bytes)
            print("BROM CRC-32 OK! Chip name: {}, BROM version: {}, BROM size: {} bytes".format(chip_name, version_string, size))

            return 0
        except ValueError:
            pass

    print("Error: Failed to validate BROM CRC-32.", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
