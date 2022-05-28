#!/usr/bin/env python3

import argparse
import sys

import yaml


ADDR_FORMATS = {
    "sfr": "SFR:0x{:02X}",
    "xdata": "EXTMEM:0x{:04X}",
}


def main():
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
