#!/usr/bin/env python3

import argparse
import sys
from zlib import crc32

try:
    import asm_fw
except ModuleNotFoundError:
    print("Error: Failed to import \"asm_fw.py\". Please run \"make\" in the root directory of this repository to generate that file, then try running this script again.", file=sys.stderr)
    sys.exit(1)


def checksum(data : bytes):
    return sum(data) & 0xff

def validate_checksum(name, data, expected):
    calc_csum = checksum(data)
    exp_csum = expected
    if calc_csum != exp_csum:
        print("Error: Invalid {} checksum: expected {:#04x}, got: {:#04x}".format(name, exp_csum, calc_csum), file=sys.stderr)
        sys.exit(1)
    print("{} checksum OK!".format(name.capitalize()))

def validate_crc32(name, data, expected):
    calc_crc32 = crc32(data)
    exp_crc32 = expected
    if calc_crc32 != exp_crc32:
        print("Error: Invalid {} crc32: expected {:#010x}, got: {:#010x}".format(name, exp_crc32, calc_crc32), file=sys.stderr)
        sys.exit(1)
    print("{} CRC32 OK!".format(name.capitalize()))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=str, help="The ASM1142/ASM2142/ASM3142 firmware binary.")
    args = parser.parse_args()

    fw_bytes = open(args.firmware, 'rb').read()
    fw = asm_fw.AsmFw.from_bytes(fw_bytes)

    header_bytes = fw_bytes[:fw.header.len]
    validate_checksum("header", header_bytes, fw.header.checksum)
    validate_crc32("header", header_bytes, fw.header.crc32)

    validate_checksum("body", fw.body.firmware.code, fw.body.checksum)
    validate_crc32("body", fw.body.firmware.code, fw.body.crc32)

    try:
        print("Body signature: {}".format(fw.body.signature.data.hex()))
    except AttributeError:
        pass

    chip_name = {
        "U2104_RCFG": "ASM1042",
        "2104B_RCFG": "ASM1042A",
        "2114A_RCFG": "ASM1142",
        "2214A_RCFG": "ASM2142/ASM3142",
        "2324A_RCFG": "ASM3242",
    }.get(fw.header.magic, "UNKNOWN (\"{}\")".format(fw.header.magic))
    print("Chip: {}".format(chip_name))

    version_string = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*fw.body.firmware.version)
    print("Firmware version: {}".format(version_string))


if __name__ == "__main__":
    main()
