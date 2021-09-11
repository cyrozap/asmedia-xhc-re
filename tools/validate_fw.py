#!/usr/bin/env python3

import argparse
import pathlib
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
    project_dir = pathlib.Path(__file__).resolve().parents[1]
    default_data_dir = str(project_dir/"data")

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-dir", type=str, default=default_data_dir, help="The YAML data directory. Default is \"{}\"".format(default_data_dir))
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

    reg_names = []
    chip_data_yaml = {
        "U2104_RCFG": "regs-asm1042.yaml",
        "2104B_RCFG": "regs-asm1042a.yaml",
        "2114A_RCFG": "regs-asm1142.yaml",
        "2214A_RCFG": "regs-asm2142.yaml",
        "2324A_RCFG": "regs-asm3242.yaml",
    }.get(fw.header.magic, None)
    if chip_data_yaml:
        try:
            yaml_path = pathlib.Path(args.data_dir) / chip_data_yaml

            import yaml
            doc = yaml.safe_load(open(yaml_path, 'r'))
            xdata = doc.get('registers', dict()).get('xdata', [])
            for reg in xdata:
                start = reg['start']
                end = reg['end']
                name = reg['name']
                reg_names.append((start, end, name))
        except FileNotFoundError:
            pass
        except ModuleNotFoundError:
            pass

    mmio_offset = {
        "U2104_RCFG": 0,
        "2104B_RCFG": 0,
        "2114A_RCFG": 0,
        "2214A_RCFG": 0x10000,
        "2324A_RCFG": 0x10000,
    }.get(fw.header.magic, 0x10000)
    header_printed = False
    for config_word in fw.header.data.config_words:
        if isinstance(config_word.info, asm_fw.AsmFw.Header.ConfigWord.WriteData):
            if not header_printed:
                print("Header MMIO writes:")
                header_printed = True

            info = config_word.info
            addr = info.addr + mmio_offset
            addr_format = "0x{:04x}"
            if mmio_offset >= 0x10000:
                addr_format = "0x{:05x}"
            formatted_addr = addr_format.format(addr)
            value_format = {
                1: '0x{:02x}',
                2: '0x{:04x}',
                4: '0x{:08x}',
            }.get(info.size)
            formatted_value = value_format.format(info.value)

            for start, end, name in reg_names:
                if addr in range(start, end + 1):
                    formatted_addr = "{}[{}] ({})".format(name, addr-start, formatted_addr)
            print("  {} <= {}".format(formatted_addr, formatted_value))


if __name__ == "__main__":
    main()
