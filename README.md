# ASMedia xHC RE


## Quick start

### Software dependencies

* Python 3
* Firmware image parser:
  * [Kaitai Struct Compiler][ksc]
  * [Kaitai Struct Python Runtime][kspr]
* Documentation generator:
  * [Asciidoctor][asciidoctor]
  * [lxml][lxml]
  * [Python-Markdown][python-markdown]
  * [PyYAML][pyyaml]

### Procedure

1. Install dependencies.
2. Run `make` to generate the parser code used by
   `tools/validate_fw.py`.
3. Obtain the firmware binaries you're interested in. You can download
   some installer executables from the links in [this file][urls].
   They're self-extracting archives, so you can use the `7z` utility to
   extract the executable inside. Use `wine` to run the extracted
   executable (no need to finish the install), then grab the files it
   extracts from the Wine user's TEMP folder.
4. Explore the firmware with [the Kaitai Web IDE][ide] and the
   [Kaitai Struct definition file][ksy], or run `./tools/validate_fw.py`
   to check the integrity and version of the firmware.
5. Run `make doc` to generate XHTML documentation in [doc/out][doc].


## Reverse engineering notes

See [doc/Notes.md](doc/Notes.md).


## Project status

Overall, maybe 30% of the chip's functionality is understood. Much more
reverse engineering work is needed before work on a FOSS replacement firmware
can begin.


### Detailed overview

* It's possible to build and load arbitrary code for all ASMedia USB host
  controllers released before March 2023.
  * Almost all the parts of the firmware image that are read by the boot ROMs
    are understood completely.
    * The first 4 bytes appear to be the offset of the next image, but this
      hasn't been confirmed.
    * The bytes between the 16-byte header and the configuration words are
      never read by the boot ROM and have an unknown purpose.
  * Firmware images can be booted from flash (written using an external SPI
    flash programmer).
  * Some chips can have their code loaded directly by the host over PCIe,
    without having to write it to flash.
    * Only the ASM1042A, ASM1142, and ASM2142/ASM3142 are currently supported.
* MMIO peripherals (ASM1142 only):
  * Timer is 100% understood (including errata).
  * UART is 99% understood.
    * There are some registers and bits in registers whose functionality is
      not entirely understood, but enough of the UART is understood well
      enough for most practical purposes.
    * For instance, bits 1-7 in `UART_LSR` have meanings that have been
      difficult to determine experimentally, but they aren't needed for simply
      sending and receiving data.
  * PCIe functionality is maybe only 40% understood.
    * Software-managed PCIe functionality is probably 80% understood.
      * There appear to be eight distinct operations, numbered 1 through 8.
      * Of those eight, only operations 1 (write Device Context entry), 3
        (write Event TRB), and 6 (DMA read) are understood completely.
      * Operations 7 and 8 appear to be Scratchpad memory write and read
        operations, respectively, but this hasn't been confirmed.
      * Operations 2, 4, and 5 have unknown functions.
    * Hardware-managed PCIe functionality is not understood at all.
      * It's unknown whether USB transfers all pass through buffers in SRAM or
        whether the data gets send straight to the host, bypassing any
        buffering.
      * There appear to be MMIO registers where buffer addresses are getting
        set, but it's difficult to know what each MMIO buffer pointer register
        is for exactly (e.g., what the buffer is storing, where the data comes
        from, etc.).
  * USB functionality is maybe only 5% understood.
    * Most XHCI Capability Registers and Operational Registers have been
      identified.
    * Registers used by the USB Debug Class have been identified.
      * It's unknown how to get the Debug Class functionality to actually
        work. Reverse engineering this functionality is further complicated by
        the fact that it doesn't appear to work with the stock firmware (at
        least with Linux as both the debug host and device--it's possible it
        may work correctly with Windows, but this has not been tested).
    * It's not yet known how device enumeration and large data transfers are
      performed.
* SFR peripherals (ASM1142 only):
  * Most functionality is understood.
  * Some registers still need to be experimented with to finish reverse
    engineering their complete functionality, but most of them appear to be
    used simply for hardware-accelerated data movement and vector operations,
    so they're not strictly necessary.
    * Bits 0-2 of `HARD_COPY_CTRL`.
    * Bits 1-3 of `MISC_CTRL`.
    * Bits 0-2 of `0x8E` are R/W, but their purpose is not known.


## License

Except where otherwise noted:

* All software in this repository (e.g., the serial monitor and the scripts
  and tools to build it, tools for unpacking and generating firmware, tools
  for building documentation, etc.) is made available under the
  [GNU General Public License, version 3 or later][gpl].
* All copyrightable content that is not software (e.g., chip register and
  programming manuals, reverse engineering notes, this README file, etc.) is
  licensed under the
  [Creative Commons Attribution-ShareAlike 4.0 International License][cc-by-sa].


[ksc]: https://github.com/kaitai-io/kaitai_struct_compiler
[kspr]: https://github.com/kaitai-io/kaitai_struct_python_runtime
[asciidoctor]: https://asciidoctor.org/
[lxml]: https://lxml.de/
[python-markdown]: https://python-markdown.github.io/
[pyyaml]: https://pyyaml.org/
[urls]: doc/firmware-urls.txt
[ide]: https://ide.kaitai.io/
[ksy]: tools/asm_fw.ksy
[doc]: doc/out
[gpl]: COPYING.txt
[cc-by-sa]: https://creativecommons.org/licenses/by-sa/4.0/
