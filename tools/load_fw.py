#!/usr/bin/env python3

import argparse
import time

from asm_tool import AsmDev


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dbsf", type=str, help="The \"<domain>:<bus>:<slot>.<func>\" for the ASMedia USB 3 host controller.")
    parser.add_argument("firmware", type=str, help="The raw firmware binary to load.")
    args = parser.parse_args()

    dev = AsmDev(args.dbsf)
    print("Chip: {}".format(dev.name))

    binary = open(args.firmware,'rb').read()
    if len(binary) % 2:
        binary += b'\0'
    start = time.perf_counter_ns()
    dev.hw_code_load_exec(binary)
    stop = time.perf_counter_ns()
    print("Loaded {} bytes in {:.06f} seconds ({} bytes/second)".format(len(binary), (stop-start)/1e9, int(len(binary)*1000000000/(stop-start))))


if __name__ == "__main__":
    main()
