#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# validate_brom.py - A tool to validate that a boot ROM was dumped properly.
# Copyright (C) 2021, 2024-2025  Forest Crossman <cyrozap@gmail.com>
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
import csv
import io
import struct
import sys
from hashlib import md5, sha1, sha256, sha512, blake2b
from zlib import crc32


CHIPS: dict[bytes, str] = {
    bytes(8): "ASM1042",
    b"2104B_FW": "ASM1042A",
    b"2114A_FW": "ASM1142",
    b"2214A_FW": "ASM2142/ASM3142",
    b"2324A_FW": "ASM3242",
    b"3306A_FW": "ASM3063/Prom",
    b"3306B_FW": "ASM3063A/PromLP",
    b"3308A_FW": "ASM3083/Prom19",
    b"3328A_FW": "ASM3283/Prom21",
}


def validate_crc32(data: bytes, expected: int) -> None:
    calc_crc32: int = crc32(data)
    if calc_crc32 != expected:
        raise ValueError("Invalid CRC-32: expected {:#010x}, got: {:#010x}".format(expected, calc_crc32))

def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv", default=False, action="store_true", help="Output in CSV format.")
    parser.add_argument("firmware", type=str, help="The ASMedia USB 3 host controller boot ROM binary.")
    args: argparse.Namespace = parser.parse_args()

    fw_bytes: bytes
    with open(args.firmware, "rb") as f:
        fw_bytes = f.read()

    chip_magic: bytes = fw_bytes[0x87:0x87+8]
    chip_name: str = CHIPS.get(chip_magic, "Unknown magic: {!r}".format(chip_magic))

    for size in (0x8000, 0x10000):
        expected: int = struct.unpack_from('<I', fw_bytes, size-4)[0]

        try:
            validate_crc32(fw_bytes[:size-4], expected)

            version_bytes: bytes = fw_bytes[0x80:0x80+6]
            version_string: str = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*version_bytes)
            if args.csv:
                hashes: list[str] = []
                for hash_alg in (md5, sha1, sha256, sha512, blake2b):
                    # Calculate hashes on the 32 kB / 64 kB BROM (includes the CRC-32)
                    hashes.append(hash_alg(fw_bytes[:size], usedforsecurity=False).hexdigest())
                with io.StringIO(newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([chip_name, version_string, size, "0x{:08X}".format(expected)] + hashes)
                    print(csvfile.getvalue().rstrip())
            else:
                print("BROM CRC-32 OK! Chip name: {}, BROM version: {}, BROM size: {} bytes, BROM CRC-32: 0x{:08X}".format(
                    chip_name, version_string, size, expected))

            return 0
        except ValueError:
            pass

    print("Error: Failed to validate BROM CRC-32.", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
