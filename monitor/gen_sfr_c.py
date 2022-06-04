#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# gen_sfr_c.py - Helper script to generate SFR read/write code.
# Copyright (C) 2020-2021  Forest Crossman <cyrozap@gmail.com>
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
import string


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=str, help="Template file.")
    parser.add_argument("-o", "--output", type=str, default="sfr.c", help="Output C file.")
    args = parser.parse_args()

    template = string.Template(open(args.template, 'r').read())

    sfr_range = range(0x80, 0x100)

    sfr_defs = []
    for i in sfr_range:
        sfr_defs.append("static SFR(SFR_{0:02X}, 0x{0:02X});".format(i))

    get_cases = []
    for i in sfr_range:
        get_cases.append("\tcase 0x{0:02X}:\n\t\treturn SFR_{0:02X};".format(i))

    set_cases = []
    for i in sfr_range:
        if i in (0x81, 0x82, 0x83, 0xD0, 0xE0, 0xF0):
            # Disable writes to critical SFRs.
            continue
        set_cases.append("\tcase 0x{0:02X}:\n\t\tSFR_{0:02X} = value;\n\t\tbreak;".format(i))

    mapping = {
        'SFR_DEFS': '\n'.join(sfr_defs),
        'GET_CASES': '\n'.join(get_cases),
        'SET_CASES': '\n'.join(set_cases),
    }

    generated = template.substitute(mapping)

    output = open(args.output, 'w')
    output.write(generated)
    output.close()


if __name__ == "__main__":
        main()
