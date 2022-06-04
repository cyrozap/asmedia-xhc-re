#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# validate_brom.py - A tool to validate that a boot ROM was dumped properly.
# Copyright (C) 2021  Forest Crossman <cyrozap@gmail.com>
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


def validate_crc32(data, expected):
    calc_crc32 = crc32(data)
    exp_crc32 = expected
    if calc_crc32 != exp_crc32:
        raise ValueError("Invalid CRC32: expected {:#010x}, got: {:#010x}".format(exp_crc32, calc_crc32))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=str, help="The ASMedia USB 3 host controller boot ROM binary.")
    args = parser.parse_args()

    fw_bytes = open(args.firmware, 'rb').read()

    for size in (0x8000, 0x10000):
        expected = struct.unpack_from('<I', fw_bytes, size-4)[0]

        try:
            validate_crc32(fw_bytes[:size-4], expected)

            version_bytes = fw_bytes[0x80:0x80+6]
            version_string = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*version_bytes)
            print("BROM CRC32 OK! BROM version: {}, BROM size: {} bytes".format(version_string, size))

            return 0
        except ValueError:
            pass

    print("Error: Failed to validate BROM CRC32.", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
