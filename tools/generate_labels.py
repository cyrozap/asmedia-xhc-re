#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# generate_labels.py - A tool to generate a list of labels for Ghidra from a
# YAML file containing register definitions.
# Copyright (C) 2022, 2025  Forest Crossman <cyrozap@gmail.com>
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
import sys

import yaml  # type: ignore[import-untyped]


ADDR_FORMATS = {
    "sfr": "SFR:0x{:02X}",
    "xdata": "EXTMEM:0x{:04X}",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=str, help="The output file. Defaults to stdout if not specified.")
    parser.add_argument("input", type=str, help="The input YAML register definition file.")
    args = parser.parse_args()

    doc = yaml.safe_load(open(args.input, 'r'))

    output = sys.stdout
    if args.output:
        output = open(args.output, 'w')

    register_regions = doc.get('registers', dict())
    for region_name, region_registers in register_regions.items():
        if region_name not in ADDR_FORMATS.keys():
            continue

        addr_format = ADDR_FORMATS[region_name]
        for register in region_registers:
            reg_name = register.get('name', "")
            if not reg_name:
                continue

            start = register.get('start')
            if start is None:
                continue

            addr_string = addr_format.format(start)

            label = "{} {} l\n".format(reg_name, addr_string)
            output.write(label)

    output.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
