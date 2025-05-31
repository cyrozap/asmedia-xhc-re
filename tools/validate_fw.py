#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# validate_fw.py - A tool to validate a firmware image.
# Copyright (C) 2020-2021, 2025  Forest Crossman <cyrozap@gmail.com>
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
import pathlib
import sys
from typing import Callable
from zlib import crc32

try:
    import asm_fw
except ModuleNotFoundError:
    print("Error: Failed to import \"asm_fw.py\". Please run \"make\" in the root directory of this repository to generate that file, then try running this script again.", file=sys.stderr)
    sys.exit(1)

try:
    import prom_fw
except ModuleNotFoundError:
    print("Error: Failed to import \"prom_fw.py\". Please run \"make\" in the root directory of this repository to generate that file, then try running this script again.", file=sys.stderr)
    sys.exit(1)


def checksum(data: bytes) -> int:
    return sum(data) & 0xff

def promontory_checksum(data: bytes) -> int:
    return sum(data) & 0xffffffff

def validate_checksum(name: str, data: bytes, expected: int, function: Callable[[bytes], int] = checksum) -> None:
    calc_csum: int = function(data)
    exp_csum: int = expected
    if calc_csum != exp_csum:
        print("Error: Invalid {} checksum: expected {:#04x}, got: {:#04x}".format(name, exp_csum, calc_csum), file=sys.stderr)
        sys.exit(1)
    print("{} checksum OK! 0x{:02x}".format(name.capitalize(), exp_csum))

def validate_crc32(name: str, data: bytes, expected: int) -> None:
    calc_crc32: int = crc32(data)
    exp_crc32: int = expected
    if calc_crc32 != exp_crc32:
        print("Error: Invalid {} crc32: expected {:#010x}, got: {:#010x}".format(name, exp_crc32, calc_crc32), file=sys.stderr)
        sys.exit(1)
    print("{} CRC32 OK! 0x{:08x}".format(name.capitalize(), exp_crc32))

def promontory(args: argparse.Namespace, fw_bytes: bytes) -> None:
    fw: prom_fw.PromFw = prom_fw.PromFw.from_bytes(fw_bytes)

    validate_checksum("code", fw.body.firmware.code, fw.header.checksum, promontory_checksum)

    try:
        print("Code signature: {}".format(fw.body.signature.data.hex()))
    except AttributeError:
        pass

    chip_name: str = {
        "3306A_FW": "ASM3063/Prom",
        "3306B_FW": "ASM3063A/PromLP",
        "3308A_FW": "ASM3083/Prom19",
        "3328A_FW": "ASM3283/Prom21",
    }.get(fw.body.firmware.magic, "UNKNOWN (\"{}\")".format(fw.body.firmware.magic))
    print("Chip: {}".format(chip_name))

    version_string: str = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*fw.body.firmware.version)
    print("Firmware version: {}".format(version_string))

    if args.extract:
        open('.'.join(args.firmware.split('.')[:-1]) + ".code.bin", 'wb').write(fw.body.firmware.code)

def main() -> None:
    project_dir: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]
    default_data_dir: str = str(project_dir/"data")

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-dir", type=str, default=default_data_dir, help="The YAML data directory. Default is \"{}\"".format(default_data_dir))
    parser.add_argument("-e", "--extract", action="store_true", default=False, help="Extract the code from the firmware image.")
    parser.add_argument("firmware", type=str, help="The ASMedia USB 3 host controller firmware image.")
    args: argparse.Namespace = parser.parse_args()

    fw_bytes: bytes = open(args.firmware, 'rb').read()
    if fw_bytes.startswith(b"_PT_"):
        return promontory(args, fw_bytes)

    fw: asm_fw.AsmFw = asm_fw.AsmFw.from_bytes(fw_bytes)

    header_bytes: bytes = fw_bytes[:fw.header.len]
    validate_checksum("header", header_bytes, fw.header.checksum)
    validate_crc32("header", header_bytes, fw.header.crc32)

    validate_checksum("code", fw.body.firmware.code, fw.body.checksum)
    validate_crc32("code", fw.body.firmware.code, fw.body.crc32)

    try:
        print("Code signature: {}".format(fw.body.signature.data.hex()))
    except AttributeError:
        pass

    chip_name: str = {
        "U2104_RCFG": "ASM1042",
        "2104B_RCFG": "ASM1042A",
        "2114A_RCFG": "ASM1142",
        "2214A_RCFG": "ASM2142/ASM3142",
        "2324A_RCFG": "ASM3242",
    }.get(fw.header.magic, "UNKNOWN (\"{}\")".format(fw.header.magic))
    print("Chip: {}".format(chip_name))

    version_string: str = "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*fw.body.firmware.version)
    print("Firmware version: {}".format(version_string))

    reg_names: list[tuple[int, int, str]] = []
    chip_data_yaml: str | None = {
        "U2104_RCFG": "regs-asm1042.yaml",
        "2104B_RCFG": "regs-asm1042a.yaml",
        "2114A_RCFG": "regs-asm1142.yaml",
        "2214A_RCFG": "regs-asm2142.yaml",
        "2324A_RCFG": "regs-asm3242.yaml",
    }.get(fw.header.magic, None)
    if chip_data_yaml:
        try:
            yaml_path: pathlib.Path = pathlib.Path(args.data_dir) / chip_data_yaml

            import yaml  # type: ignore[import-untyped]
            doc: dict[str, dict[str, list[dict]]] = yaml.safe_load(open(yaml_path, 'r'))
            xdata: list[dict] = doc.get('registers', dict()).get('xdata', [])
            for reg in xdata:
                start: int = reg['start']
                end: int = reg['end']
                name: str = reg['name']
                reg_names.append((start, end, name))
        except FileNotFoundError:
            pass
        except ModuleNotFoundError:
            pass

    mmio_offset: int = {
        "U2104_RCFG": 0,
        "2104B_RCFG": 0,
        "2114A_RCFG": 0,
        "2214A_RCFG": 0x10000,
        "2324A_RCFG": 0x10000,
    }.get(fw.header.magic, 0x10000)
    header_printed: bool = False
    for config_word in fw.header.data.config_words:
        if isinstance(config_word.info, asm_fw.AsmFw.Header.ConfigWord.WriteData):
            if not header_printed:
                print("Header MMIO writes:")
                header_printed = True

            info: asm_fw.AsmFw.Header.ConfigWord.WriteData = config_word.info
            addr: int = info.addr + mmio_offset
            addr_format: str = "0x{:04x}"
            if mmio_offset >= 0x10000:
                addr_format = "0x{:05x}"
            formatted_addr: str = addr_format.format(addr)
            value_format: str | None = {
                1: '0x{:02x}',
                2: '0x{:04x}',
                4: '0x{:08x}',
            }.get(info.size)
            if value_format is None:
                raise ValueError("Invalid config word value size: {}".format(info.size))
            formatted_value: str = value_format.format(info.value)

            for start, end, name in reg_names:
                if addr in range(start, end + 1):
                    formatted_addr = "{}[{}] ({})".format(name, addr-start, formatted_addr)
            print("  {} <= {}".format(formatted_addr, formatted_value))

    if args.extract:
        open('.'.join(args.firmware.split('.')[:-1]) + ".code.bin", 'wb').write(fw.body.firmware.code)


if __name__ == "__main__":
    main()
