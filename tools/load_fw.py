#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# load_fw.py - A tool to directly load firmware into an ASMedia USB host
# controller.
# Copyright (C) 2021-2022, 2025  Forest Crossman <cyrozap@gmail.com>
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
import time

from asm_tool import AsmDev


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dbsf", type=str, help="The \"<domain>:<bus>:<slot>.<func>\" for the ASMedia USB 3 host controller.")
    parser.add_argument("firmware", type=str, help="The raw firmware binary to load.")
    args = parser.parse_args()

    dev = AsmDev(args.dbsf)
    print("Chip: {}".format(dev.name))

    print("Unbinding the kernel driver if it's attached...")
    dev.pci.driver_unbind()

    binary = open(args.firmware,'rb').read()
    if len(binary) % 2:
        binary += b'\0'

    print("Loading \"{}\"...".format(args.firmware))
    start = time.perf_counter_ns()
    dev.hw_code_load_exec(binary)
    stop = time.perf_counter_ns()
    print("Loaded {} bytes in {:.06f} seconds ({} bytes/second)".format(len(binary), (stop-start)/1e9, int(len(binary)*1000000000/(stop-start))))


if __name__ == "__main__":
    main()
