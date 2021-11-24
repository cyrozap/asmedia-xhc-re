#!/usr/bin/env python3

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
