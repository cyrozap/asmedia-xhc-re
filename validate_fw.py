#!/usr/bin/env python3

import argparse
import sys
from zlib import crc32

try:
    import asm_fw
except ModuleNotFoundError:
    print("Error: Failed to import \"asm_fw.py\". Please run \"make\" in this directory to generate that file, then try running this script again.", file=sys.stderr)
    sys.exit(1)


def checksum(data : bytes):
    return sum(data) & 0xff

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=str, help="The ASM1142/ASM2142/ASM3142 firmware binary.")
    args = parser.parse_args()

    fw_bytes = open(args.firmware, 'rb').read()
    fw = asm_fw.AsmFw.from_bytes(fw_bytes)

    header_bytes = fw_bytes[:fw.header.len]
    calc_csum = checksum(header_bytes)
    exp_csum = fw.header.checksum
    if calc_csum != exp_csum:
        print("Error: Invalid header checksum: expected {:#04x}, got: {:#04x}".format(exp_csum, calc_csum), file=sys.stderr)
        sys.exit(1)
    print("Header checksum OK!")

    calc_crc32 = crc32(header_bytes)
    exp_crc32 = fw.header.crc32
    if calc_crc32 != exp_crc32:
        print("Error: Invalid header crc32: expected {:#010x}, got: {:#010x}".format(exp_crc32, calc_crc32), file=sys.stderr)
        sys.exit(1)
    print("Header CRC32 OK!")

    calc_csum = checksum(fw.body.firmware.code)
    exp_csum = fw.body.checksum
    if calc_csum != exp_csum:
        print("Error: Invalid body checksum: expected {:#04x}, got: {:#04x}".format(exp_csum, calc_csum), file=sys.stderr)
        sys.exit(1)
    print("Body checksum OK!")

    calc_crc32 = crc32(fw.body.firmware.code)
    exp_crc32 = fw.body.crc32
    if calc_crc32 != exp_crc32:
        print("Error: Invalid body crc32: expected {:#010x}, got: {:#010x}".format(exp_crc32, calc_crc32), file=sys.stderr)
        sys.exit(1)
    print("Body CRC32 OK!")

    version_string = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*fw.body.firmware.version)
    print("Firmware version: {}".format(version_string))


if __name__ == "__main__":
        main()
