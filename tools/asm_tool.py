#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# asm_tool.py - A library for interacting with ASMedia USB host controllers.
# Copyright (C) 2021-2022  Forest Crossman <cyrozap@gmail.com>
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
import mmap
import os
import struct
import time


class BusError(Exception):
    pass

class PciDev:
    '''Lightweight abstraction over the PCI userspace API'''

    width_map = {
        1: 'b',
        2: 'w',
        4: 'l',
    }

    struct_map = {
        1: 'B',
        2: '<H',
        4: '<I',
    }

    def __init__(self, dbsf: str, debug: bool = False, verbose: bool = False):
        self.dbsf = dbsf
        self.debug = debug
        self.verbose = debug or verbose
        self._config = open("/sys/bus/pci/devices/{}/config".format(self.dbsf), "r+b", buffering=0)

        # Check bus status.
        if self.config_reg_read(0, 4) == 0xffffffff:
            raise BusError("Can't access device.")

        self.vid = int(open("/sys/bus/pci/devices/{}/vendor".format(self.dbsf), "r").read().rstrip('\n'), 16)
        self.did = int(open("/sys/bus/pci/devices/{}/device".format(self.dbsf), "r").read().rstrip('\n'), 16)

        self._mmap = None

    def config_reg_read(self, reg: int, width: int):
        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("PciDev.config_reg_read: Reading {} bytes from {:#x}...".format(width, reg))

        self._config.seek(reg)
        raw = self._config.read(width)
        assert len(raw) == width
        value = struct.unpack(self.struct_map[width], raw)[0]

        if self.debug:
            print("PciDev.config_reg_read: Read: {:#x}".format(value))

        return value

    def config_reg_write(self, reg: int, width: int, value: int, confirm: bool = False):
        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("PciDev.config_reg_write: Writing {} bytes of {:#x} to {:#x}...".format(width, value, reg))

        self._config.seek(reg)
        self._config.write(struct.pack(self.struct_map[width], value))
        self._config.flush()

        # If "confirm" is set, repeatedly read the register until its contents
        # match the value written.
        if confirm:
            while self.config_reg_read(reg, width) != value:
                continue

    def bar0_reg_read(self, reg: int, width: int):
        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("PciDev.bar0_reg_read: Reading {} bytes from {:#x}...".format(width, reg))

        if self._mmap == None:
            fd = os.open('/sys/bus/pci/devices/{}/resource0'.format(self.dbsf), os.O_RDWR)
            self._mmap = mmap.mmap(fd, 0)

        # Reads need to be performed in one transaction, but
        # struct.unpack_from performs one read for every byte. Work around
        # this limitation by performing the read and unpacking the value in
        # two separate steps.
        value = struct.unpack(self.struct_map[width], self._mmap[reg:reg+width])[0]

        if self.debug:
            print("PciDev.bar0_reg_read: Read: {:#x}".format(value))

        return value

    def bar0_reg_write(self, reg: int, width: int, value: int, confirm: bool = False):
        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("PciDev.bar0_reg_write: Writing {} bytes of {:#x} to {:#x}...".format(width, value, reg))

        if self._mmap == None:
            fd = os.open('/sys/bus/pci/devices/{}/resource0'.format(self.dbsf), os.O_RDWR)
            self._mmap = mmap.mmap(fd, 0)

        # Writes need to be performed in one transaction, but struct.pack_into
        # performs one write for every byte. Work around this limitation by
        # packing the value and performing the write in two separate steps.
        data = struct.pack(self.struct_map[width], value)
        self._mmap[reg:reg+width] = data

        # If "confirm" is set, repeatedly read the register until its contents
        # match the value written.
        if confirm:
            while self.bar0_reg_read(reg, width) != value:
                continue

class AsmDev:
    width_map = {
        1: 'b',
        2: 'w',
        4: 'l',
    }

    struct_map = {
        1: 'B',
        2: '<H',
        4: '<I',
        8: '<Q',
    }

    # TODO: Populate structs with register info from YAML files.
    ids_map = {
        (0x1b21, 0x1042): {
            'name': "ASM1042",
            'hw_code_and_mmio': None,
        },
        (0x1b21, 0x1142): {
            'name': "ASM1042A",
            'hw_code_and_mmio': 1,
        },
        (0x1b21, 0x1242): {
            'name': "ASM1142",
            'hw_code_and_mmio': 1,
        },
        (0x1b21, 0x2142): {
            'name': "ASM2142/ASM3142",
            'hw_code_and_mmio': 2,
        },
        (0x1b21, 0x3242): {
            'name': "ASM3242",
            # Not sure if HW MMIO access is missing or just locked-out.
        },
    }

    CODE_RAM_ADDR = 0xE2

    CODE_RAM_DATA_LOWER_BANK_DATA = 0xE4
    CODE_RAM_DATA_UPPER_BANK_DATA = 0xE6
    MMIO_ACCESS_ADDR = 0xE8
    MMIO_ACCESS_WRITE_DATA = 0xEA
    MMIO_ACCESS_READ_DATA = 0xEB

    CODE_RAM_WRITE_DATA_BAR0 = 0x3010
    CODE_RAM_READ_DATA_BAR0 = 0x3018
    MMIO_ACCESS_ADDR_BAR0 = 0x3000
    MMIO_ACCESS_WRITE_DATA_BAR0 = 0x3004
    MMIO_ACCESS_READ_DATA_BAR0 = 0x3008
    MMIO_ACCESS_STATUS_BAR0 = 0x3009

    CPU_MODE_NEXT_64K = 0xF340
    CPU_EXEC_CTRL_64K = 0xF342

    CPU_MODE_NEXT_128K = 0x15040
    CPU_EXEC_CTRL_128K = 0x15042

    def __init__(self, dbsf: str, debug: bool = False, verbose: bool = False):
        self.debug = debug
        self.verbose = debug or verbose
        self.pci = PciDev(dbsf, debug, verbose)

        vid = self.pci.vid
        did = self.pci.did
        if (vid, did) not in self.ids_map.keys():
            raise KeyError("Unrecognized PCI VID:DID pair: {:04x}:{:04x}".format(vid, did))

        self.chip = self.ids_map[(vid, did)]
        self.name = self.chip['name']
        self.hw_code_and_mmio = self.chip.get('hw_code_and_mmio', None)

    def hw_code_write(self, addr: int, code: bytes):
        if self.hw_code_and_mmio not in (1, 2):
            raise ValueError("{} is not capable of hardware CODE access.".format(self.name))

        if not (addr >= 0 and addr <= 0xfffe):
            raise ValueError("Invalid address, must be >= 0x0000 and <= 0xFFFE: {:#x}".format(addr))

        if addr % 2 != 0:
            raise ValueError("Invalid address, must be 2-byte aligned: 0x{:04x}".format(addr))

        code_size_limit = 0x10000
        if self.hw_code_and_mmio == 2:
            code_size_limit = 0x18000

        if len(code) > code_size_limit:
            raise ValueError("Invalid code length, must be less than {:#x}: {:#x}".format(code_size_limit, len(code)))

        if len(code) % 2 != 0:
            raise ValueError("Invalid code length, must be a multiple of 2: 0x{:04x}".format(len(code)))

        # Enable hardware CODE write access.
        if self.hw_code_and_mmio == 1:
            reg_F343 = self.hw_mmio_reg_read(0xF343, 1)
            self.hw_mmio_reg_write(0xF343, 1, reg_F343 | (1 << 1), confirm=True)
        elif self.hw_code_and_mmio == 2:
            reg_1500E = self.hw_mmio_reg_read(0x1500E, 1)
            self.hw_mmio_reg_write(0x1500E, 1, reg_1500E | (1 << 0), confirm=True)
            self.pci.config_reg_write(0xef, 1, 1 << 7, confirm=True)

        # Write to CODE memory.
        if self.hw_code_and_mmio == 1:
            for i, (word,) in enumerate(struct.iter_unpack('<H', code)):
                offset_addr = addr + (i * 2)

                reg = self.CODE_RAM_DATA_LOWER_BANK_DATA
                if (offset_addr & (1 << 15)):
                    reg = self.CODE_RAM_DATA_UPPER_BANK_DATA

                masked_addr = offset_addr & 0x7ffe
                self.pci.config_reg_write(self.CODE_RAM_ADDR, 2, masked_addr, confirm=True)
                self.pci.config_reg_write(reg, 2, word)
                while self.pci.config_reg_read(self.CODE_RAM_ADDR, 2) == masked_addr:
                    pass
        elif self.hw_code_and_mmio == 2:
            i = 0
            while i < len(code):
                word_ev = struct.unpack_from('<H', code, i)[0]
                word_od = 0

                word_od_i = i + 0x8000
                if word_od_i < len(code):
                    word_od = struct.unpack_from('<H', code, word_od_i)[0]

                data = struct.unpack('<I', struct.pack('<HH', word_ev, word_od))[0]

                offset_addr = addr + i
                masked_addr = ((offset_addr & 0x10000) >> 1) | (offset_addr & 0x7ffe)
                self.pci.config_reg_write(self.CODE_RAM_ADDR, 2, masked_addr, confirm=True)
                self.pci.bar0_reg_write(self.CODE_RAM_WRITE_DATA_BAR0, 4, data)
                while self.pci.config_reg_read(self.CODE_RAM_ADDR, 2) == masked_addr:
                    pass

                i += 2

                if i & 0x8000:
                    i -= 0x8000
                    i += 0x10000

            # Enable hardware CODE read access.
            self.pci.config_reg_write(0xef, 1, self.pci.config_reg_read(0xef, 1) | (1 << 6), confirm=True)

            # Read back firmware
            readback = bytearray(len(code))
            i = 0
            while i < len(code):
                offset_addr = addr + i
                masked_addr = ((offset_addr & 0x10000) >> 1) | (offset_addr & 0x7ffe)
                self.pci.config_reg_write(self.CODE_RAM_ADDR, 2, masked_addr, confirm=True)
                self.pci.bar0_reg_write(self.CODE_RAM_WRITE_DATA_BAR0, 4, 0)
                while self.pci.config_reg_read(self.CODE_RAM_ADDR, 2) == masked_addr:
                    pass

                word_ev, word_od = struct.unpack('<HH', struct.pack('<I', self.pci.bar0_reg_read(self.CODE_RAM_READ_DATA_BAR0, 4)))

                struct.pack_into('<H', readback, i, word_ev)
                word_od_i = i + 0x8000
                if word_od_i < len(code):
                    struct.pack_into('<H', readback, word_od_i, word_od)

                word_ev_2, word_od_2 = struct.unpack('<HH', struct.pack('<I', self.pci.bar0_reg_read(self.CODE_RAM_READ_DATA_BAR0+4, 4)))

                word_ev_2_i = i + 0x4000
                if word_ev_2_i < len(code):
                    struct.pack_into('<H', readback, word_ev_2_i, word_ev_2)
                word_od_2_i = i + 0x8000 + 0x4000
                if word_od_2_i < len(code):
                    struct.pack_into('<H', readback, word_od_2_i, word_od_2)

                i += 2

                if i & 0x4000:
                    i -= 0x4000
                    i += 0x10000

            assert readback == code

        # Disable hardware CODE write access.
        if self.hw_code_and_mmio == 1:
            reg_F343 = self.hw_mmio_reg_read(0xF343, 1)
            self.hw_mmio_reg_write(0xF343, 1, reg_F343 & ~(1 << 1), confirm=True)
        elif self.hw_code_and_mmio == 2:
            self.pci.config_reg_write(0xef, 1, 0, confirm=True)
            reg_1500E = self.hw_mmio_reg_read(0x1500E, 1)
            self.hw_mmio_reg_write(0x1500E, 1, reg_1500E & ~(1 << 0), confirm=True)

    def hw_code_load_exec(self, code: bytes, half_speed: bool = True):
        if self.hw_code_and_mmio not in (1, 2):
            raise ValueError("{} is not capable of hardware CODE access.".format(self.name))

        code_size_limit = 0x10000
        if self.hw_code_and_mmio == 2:
            code_size_limit = 0x18000

        if len(code) > code_size_limit:
            raise ValueError("Invalid code length, must be less than {:#x}: {:#x}".format(code_size_limit, len(code)))

        if len(code) % 2 != 0:
            raise ValueError("Invalid code length, must be a multiple of 2: 0x{:04x}".format(len(code)))

        if self.hw_code_and_mmio == 1:
            cpu_mode_next = self.CPU_MODE_NEXT_64K
            cpu_exec_ctrl = self.CPU_EXEC_CTRL_64K
        elif self.hw_code_and_mmio == 2:
            cpu_mode_next = self.CPU_MODE_NEXT_128K
            cpu_exec_ctrl = self.CPU_EXEC_CTRL_128K

        # Halt the CPU.
        self.hw_mmio_reg_write(cpu_exec_ctrl, 1, 1 << 1)

        # Write the program to CODE RAM.
        self.hw_code_write(0x0000, code)

        # Configure CPU to boot from CODE RAM.
        self.hw_mmio_reg_write(cpu_mode_next, 1, ((1 if half_speed else 0) << 1) | 1)

        # Release the CPU from reset.
        self.hw_mmio_reg_write(cpu_exec_ctrl, 1, 0)

    def hw_mmio_reg_read(self, addr: int, width: int):
        if self.hw_code_and_mmio not in (1, 2):
            raise ValueError("{} is not capable of hardware MMIO access.".format(self.name))

        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("AsmDev.hw_mmio_reg_read: Reading {} bytes from {:#x}...".format(width, addr))

        value = 0
        for i in range(width):
            byte_addr = (addr + i) & 0xffff
            if self.hw_code_and_mmio == 1:
                self.pci.config_reg_write(self.MMIO_ACCESS_ADDR, 2, byte_addr, confirm=True)
                time.sleep(0.0001)
                byte_value = self.pci.config_reg_read(self.MMIO_ACCESS_READ_DATA, 1)
                time.sleep(0.0001)
            elif self.hw_code_and_mmio == 2:
                while self.pci.bar0_reg_read(self.MMIO_ACCESS_STATUS_BAR0, 1) & (1 << 7):
                    pass
                self.pci.bar0_reg_write(self.MMIO_ACCESS_ADDR_BAR0, 2, byte_addr)
                while self.pci.bar0_reg_read(self.MMIO_ACCESS_STATUS_BAR0, 1) & (1 << 7):
                    pass
                byte_value = self.pci.bar0_reg_read(self.MMIO_ACCESS_READ_DATA_BAR0, 1)

            value |= byte_value << (8 * i)

        if self.debug:
            print("AsmDev.hw_mmio_reg_read: Read: {:#x}".format(value))

        return value

    def hw_mmio_reg_write(self, addr: int, width: int, value: int, confirm: bool = False):
        if self.hw_code_and_mmio not in (1, 2):
            raise ValueError("{} is not capable of hardware MMIO access.".format(self.name))

        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("AsmDev.hw_mmio_reg_write: Writing {} bytes of {:#x} to {:#x}...".format(width, value, addr))

        for i in range(width):
            byte_addr = (addr + i) & 0xffff
            byte_value = (value >> (8 * i)) & 0xff
            if self.hw_code_and_mmio == 1:
                self.pci.config_reg_write(self.MMIO_ACCESS_ADDR, 2, byte_addr, confirm=True)
                time.sleep(0.0001)
                self.pci.config_reg_write(self.MMIO_ACCESS_WRITE_DATA, 1, byte_value)
                time.sleep(0.0001)
            elif self.hw_code_and_mmio == 2:
                self.pci.bar0_reg_write(self.MMIO_ACCESS_ADDR_BAR0, 2, byte_addr)
                while self.pci.bar0_reg_read(self.MMIO_ACCESS_STATUS_BAR0, 1) & (1 << 7):
                    pass
                self.pci.bar0_reg_write(self.MMIO_ACCESS_WRITE_DATA_BAR0, 1, byte_value)
                while self.pci.bar0_reg_read(self.MMIO_ACCESS_STATUS_BAR0, 1) & (1 << 7):
                    pass

        # If "confirm" is set, repeatedly read the register until its contents
        # match the value written.
        if confirm:
            while self.hw_mmio_reg_read(addr, width) != value:
                continue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dbsf", type=str, help="The \"<domain>:<bus>:<slot>.<func>\" for the ASMedia USB 3 host controller.")
    args = parser.parse_args()

    dev = AsmDev(args.dbsf)
    print("Chip: {}".format(dev.name))


if __name__ == "__main__":
    main()
