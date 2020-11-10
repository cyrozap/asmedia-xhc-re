#!/usr/bin/env python3

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
