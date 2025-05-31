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
from typing import Callable, NamedTuple
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


class ChipInfo(NamedTuple):
    name: str
    data_filename: str | None
    mmio_offset: int


CHIP_INFO: dict[str, ChipInfo] = {
    "U2104": ChipInfo("ASM1042", "regs-asm1042.yaml", 0),
    "2104B": ChipInfo("ASM1042A", "regs-asm1042a.yaml", 0),
    "2114A": ChipInfo("ASM1142", "regs-asm1142.yaml", 0),
    "2214A": ChipInfo("ASM2142/ASM3142", "regs-asm2142.yaml", 0x10000),
    "2324A": ChipInfo("ASM3242", "regs-asm3242.yaml", 0x10000),
    "3306A": ChipInfo("ASM3063/Prom", None, 0x10000),
    "3306B": ChipInfo("ASM3063A/PromLP", None, 0x10000),
    "3308A": ChipInfo("ASM3083/Prom19", None, 0x10000),
    "3328A": ChipInfo("ASM3283/Prom21", None, 0x10000),
}


def checksum8(data: bytes) -> int:
    return sum(data) & 0xff

def checksum32(data: bytes) -> int:
    return sum(data) & 0xffffffff

def validate_checksum(name: str, data: bytes, expected: int, function: Callable[[bytes], int]) -> None:
    calc_csum: int = function(data)
    if calc_csum != expected:
        print("Error: Invalid {} checksum: expected {:#04x}, got: {:#04x}".format(name, expected, calc_csum), file=sys.stderr)
        sys.exit(1)
    print("{} checksum OK! 0x{:02x}".format(name.capitalize(), expected))

def validate_crc32(name: str, data: bytes, expected: int) -> None:
    calc_crc32: int = crc32(data)
    if calc_crc32 != expected:
        print("Error: Invalid {} crc32: expected {:#010x}, got: {:#010x}".format(name, expected, calc_crc32), file=sys.stderr)
        sys.exit(1)
    print("{} CRC32 OK! 0x{:08x}".format(name.capitalize(), expected))

def format_version(version: bytes) -> str:
    return "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*version)

def promontory(args: argparse.Namespace, fw_bytes: bytes) -> prom_fw.PromFw:
    fw: prom_fw.PromFw = prom_fw.PromFw.from_bytes(fw_bytes)

    chip_id: str = fw.body.firmware.magic[:5]
    chip_info: ChipInfo = CHIP_INFO.get(chip_id, ChipInfo("UNKNOWN (\"{}\")".format(chip_id), None, 0x10000))

    print("Chip: {}".format(chip_info.name))
    print("Firmware version: {}".format(format_version(fw.body.firmware.version)))

    validate_checksum("code", fw.body.firmware.code, fw.header.checksum, checksum32)

    try:
        print("Code signature: {}".format(fw.body.signature.data.hex()))
    except AttributeError:
        pass

    return fw

def xhc(args: argparse.Namespace, fw_bytes: bytes) -> asm_fw.AsmFw:
    fw: asm_fw.AsmFw = asm_fw.AsmFw.from_bytes(fw_bytes)

    chip_id: str = fw.header.magic[:5]
    chip_info: ChipInfo = CHIP_INFO.get(chip_id, ChipInfo("UNKNOWN (\"{}\")".format(chip_id), None, 0x10000))

    print("Chip: {}".format(chip_info.name))
    print("Firmware version: {}".format(format_version(fw.body.firmware.version)))

    header_bytes: bytes = fw_bytes[:fw.header.len]
    validate_checksum("header", header_bytes, fw.header.checksum, checksum8)
    validate_crc32("header", header_bytes, fw.header.crc32)

    validate_checksum("code", fw.body.firmware.code, fw.body.checksum, checksum8)
    validate_crc32("code", fw.body.firmware.code, fw.body.crc32)

    try:
        print("Code signature: {}".format(fw.body.signature.data.hex()))
    except AttributeError:
        pass

    reg_names: list[tuple[int, int, str]] = []
    chip_data_yaml: str | None = chip_info.data_filename
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

    mmio_offset: int = chip_info.mmio_offset
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

    return fw

def main() -> None:
    project_dir: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]
    default_data_dir: str = str(project_dir/"data")

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-dir", type=str, default=default_data_dir, help="The YAML data directory. Default is \"{}\"".format(default_data_dir))
    parser.add_argument("-e", "--extract", action="store_true", default=False, help="Extract the code from the firmware image.")
    parser.add_argument("firmware", type=str, help="The ASMedia USB 3 host controller firmware image.")
    args: argparse.Namespace = parser.parse_args()

    fw: asm_fw.AsmFw | prom_fw.PromFw

    fw_bytes: bytes = open(args.firmware, 'rb').read()
    if fw_bytes.startswith(b"_PT_"):
        fw = promontory(args, fw_bytes)
    else:
        fw = xhc(args, fw_bytes)

    if args.extract:
        open('.'.join(args.firmware.split('.')[:-1]) + ".code.bin", 'wb').write(fw.body.firmware.code)


if __name__ == "__main__":
    main()
