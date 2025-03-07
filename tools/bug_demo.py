#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# bug_demo.py - A tool to demonstrate hardware bugs in ASMedia USB host
# controllers.
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

from asm_tool import AsmDev


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dbsf", type=str, help="The \"<domain>:<bus>:<slot>.<func>\" for the ASMedia USB 3 host controller.")
    args = parser.parse_args()

    dev = AsmDev(args.dbsf)
    print("Chip: {}".format(dev.name))

    if dev.hw_code_and_mmio == 1:
        cpu_mode_next = dev.CPU_MODE_NEXT_64K
        cpu_exec_ctrl = dev.CPU_EXEC_CTRL_64K
        crcr_addr_internal = 0xF638
        dcbaap_addr_internal = 0xF650
    elif dev.hw_code_and_mmio == 2:
        cpu_mode_next = dev.CPU_MODE_NEXT_128K
        cpu_exec_ctrl = dev.CPU_EXEC_CTRL_128K
        crcr_addr_internal = 0x18838
        dcbaap_addr_internal = 0x18850
    else:
        print("This chip does not support hardware-based MMIO.")
        return -1

    print("Unbinding the kernel driver if it's attached...")
    dev.pci.driver_unbind()

    # Put the 8051 in an infinite loop to prevent it from interfering.
    dev.hw_code_load_exec(b'\x80\xfe' * 100)

    # Calculate base addresses.
    operational_base = dev.pci.bar0_reg_read(0x0000, 1)
    _runtime_base = dev.pci.bar0_reg_read(0x0018, 1)

    def read_qword_internal(addr_internal) -> int:
        return (dev.hw_mmio_reg_read(addr_internal + 4, 4) << 32) | dev.hw_mmio_reg_read(addr_internal, 4)

    def write_qword_bar0(bar0_addr, value) -> None:
        dev.pci.bar0_reg_write(bar0_addr, 4, value & 0xffffffff)
        dev.pci.bar0_reg_write(bar0_addr + 4, 4, value >> 32)

    for name, opb_offset, addr_internal in (("CRCR", 0x18, crcr_addr_internal), ("DCBAAP", 0x30, dcbaap_addr_internal)):
        for value in (0, 0xffffffffffffffc0, 0x12345678abcdefc0):
            # Write the expected value to the proper address in BAR0.
            write_qword_bar0(operational_base + opb_offset, value)

            # Read the internal representation of the register.
            value_internal = read_qword_internal(addr_internal)

            print("{}: Expected 0x{:016x}, got 0x{:016x}: {}".format(
                name, value, value_internal, "OK" if value == value_internal else "ERROR: Internal value does not match what was written!"))

    # Reload firmware from flash.

    # Configure CPU to boot from CODE ROM.
    dev.hw_mmio_reg_write(cpu_mode_next, 1, 2)

    # Reset the CPU.
    dev.hw_mmio_reg_write(cpu_exec_ctrl, 1, 2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
