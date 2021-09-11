#!/usr/bin/env python3

import argparse
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

    def config_reg_read(self, reg: int, width: int):
        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("Reading {} bytes from {:#x}...".format(width, reg))

        self._config.seek(reg)
        raw = self._config.read(width)
        assert len(raw) == width
        value = struct.unpack(self.struct_map[width], raw)[0]

        if self.debug:
            print("Read: {:#x}".format(value))

        return value

    def config_reg_write(self, reg: int, width: int, value: int):
        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("Writing {} bytes of {:#x} to {:#x}...".format(width, value, reg))

        self._config.seek(reg)
        self._config.write(struct.pack(self.struct_map[width], value))
        #self._config.flush()

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
    }

    # TODO: Populate structs with register info from YAML files.
    ids_map = {
        (0x1b21, 0x1042): {
            'name': "ASM1042",
            'hw_mmio': False,
        },
        (0x1b21, 0x1142): {
            'name': "ASM1042A",
            'hw_mmio': True,
        },
        (0x1b21, 0x1242): {
            'name': "ASM1142",
            'hw_mmio': True,
        },
        (0x1b21, 0x2142): {
            'name': "ASM2142/ASM3142",
            # Not sure if HW MMIO access is missing or just locked-out.
        },
        (0x1b21, 0x3242): {
            'name': "ASM3242",
            # Not sure if HW MMIO access is missing or just locked-out.
        },
    }

    MMIO_ACCESS_ADDR = 0xE8
    MMIO_ACCESS_WRITE_DATA = 0xEA
    MMIO_ACCESS_READ_DATA = 0xEB

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
        self.hw_mmio = self.chip.get('hw_mmio', False)

    def hw_mmio_reg_read(self, addr: int, width: int):
        if not self.hw_mmio:
            raise ValueError("{} is not capable of hardware MMIO access.".format(self.name))

        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("Reading {} bytes from {:#x}...".format(width, addr))

        value = 0
        for i in range(width):
            byte_addr = (addr + i) & 0xffff
            self.pci.config_reg_write(self.MMIO_ACCESS_ADDR, 2, byte_addr)
            while True:
                byte_addr_readback = self.pci.config_reg_read(self.MMIO_ACCESS_ADDR, 2)
                if byte_addr_readback == byte_addr:
                    break
                time.sleep(0.001)
            byte_value = self.pci.config_reg_read(self.MMIO_ACCESS_READ_DATA, 1)

            value |= byte_value << (8 * i)

        if self.debug:
            print("Read: {:#x}".format(value))

        return value

    def hw_mmio_reg_write(self, addr: int, width: int, value: int):
        if not self.hw_mmio:
            raise ValueError("{} is not capable of hardware MMIO access.".format(self.name))

        if width not in self.struct_map.keys():
            raise ValueError("Invalid width: {}".format(width))

        if self.debug:
            print("Writing {} bytes of {:#x} to {:#x}...".format(width, value, addr))

        for i in range(width):
            byte_addr = (addr + i) & 0xffff
            self.pci.config_reg_write(self.MMIO_ACCESS_ADDR, 2, byte_addr)
            while True:
                byte_addr_readback = self.pci.config_reg_read(self.MMIO_ACCESS_ADDR, 2)
                if byte_addr_readback == byte_addr:
                    break
                time.sleep(0.001)
            byte_value = (value >> (8 * i)) & 0xff
            self.pci.config_reg_write(self.MMIO_ACCESS_WRITE_DATA, 1, byte_value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dbsf", type=str, help="The ASM1042A/ASM1142/ASM2142/ASM3142/ASM3242 \"<domain>:<bus>:<slot>.<func>\".")
    args = parser.parse_args()

    dev = AsmDev(args.dbsf)
    print("Chip: {}".format(dev.name))


if __name__ == "__main__":
    main()
