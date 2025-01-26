# Tools for working with ASMedia USB host controllers


## [asmedia-xhc-trace](asmedia-xhc-trace)

A Rust utility to record a trace of the program counter of the 8051 in a host
controller. Currently only works with the ASM1042A and ASM1142.


## [emulator](emulator)

This is where I'd put my custom host controller emulator (if I had one). For now
it just contains some of my thoughts on how I'd write an 8051 emulator.


## [ghidra-scripts](ghidra-scripts)

Scripts for [Ghidra][ghidra] that can help with reverse engineering host
controller firmware.


## [asm\_fw.ksy](asm_fw.ksy)

A [Kaitai Struct][kaitai] definition for the ASMedia USB host controller
firmware image format.


## [asm\_tool.py](asm_tool.py)

A Python library for interacting with ASMedia USB host controllers over PCIe.
Can be used to read and write internal MMIO registers and load/execute arbitrary
code on certain host controllers. Currently only the ASM1042A, ASM1142, and
ASM2142/ASM3142 are supported.


## [bug\_demo.py](bug_demo.py)

This tool uses the [asm\_tool](asm_tool.py) library to demonstrate the hardware
bug present on all 64-bit ASMedia USB host controllers that prevents them from
accessing the xHCI Command Ring if the Command Ring is located at an address
greater than or equal to 0x0001000000000000. The program works by writing the
CRCR and DCBAAP registers in PCI BAR0, then reading them back through the
indirect internal MMIO register access mechanism to see how the 8051 core sees
the values in those registers.

Currently only the ASM1042A, ASM1142, and ASM2142/ASM3142 are supported.

Example output:

```
Chip: ASM1042A
Unbinding the kernel driver if it's attached...
CRCR: Expected 0x0000000000000000, got 0x0000000000000000: OK
CRCR: Expected 0xffffffffffffffc0, got 0xff00ffffffffffc0: ERROR: Internal value does not match what was written!
CRCR: Expected 0x12345678abcdefc0, got 0x34005678abcdefc0: ERROR: Internal value does not match what was written!
DCBAAP: Expected 0x0000000000000000, got 0x0000000000000000: OK
DCBAAP: Expected 0xffffffffffffffc0, got 0xffffffffffffffc0: OK
DCBAAP: Expected 0x12345678abcdefc0, got 0x12345678abcdefc0: OK
```


## [generate\_docs.py](generate_docs.py)

This is a Python script that generates XHTML documentation pages from the YAML
register definitions in the [data][data] directory.


## [generate\_labels.py](generate_labels.py)

This Python script can use the YAML register definitions in the [data][data]
directory to generate a list of memory address labels that can be imported into
Ghidra.


## [load\_fw.py](load_fw.py)

This tool provides a convenient way to directly load code into a host controller
and execute it without having to first write the code to flash.

Currently only the ASM1042A, ASM1142, and ASM2142/ASM3142 are supported.


## [prom\_fw.ksy](prom_fw.ksy)

A [Kaitai Struct][kaitai] definition for the Promontory chipset firmware image
format.


## [validate\_brom.py](validate_brom.py)

Validates a BROM (boot ROM/mask ROM) dump by verifying the CRC-32 checksum
embedded in the image. Also prints BROM version information.


## [validate\_fw.py](validate_fw.py)

Validates a flash firmware image by verifying the various checksums in the
image. Also prints the firmware version and lists the registers/values set by
the sequence of config words in the header.


[ghidra]: https://ghidra-sre.org/
[kaitai]: https://kaitai.io/
[data]: ../data
