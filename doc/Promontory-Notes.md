# Notes on Promontory Chips


## Design

Despite being branded by AMD, Promontory chips use an architecture that is very similar to that of ASMedia's USB host controllers.
Like ASMedia's USB host controllers, Promontory chips are controlled by an 8051 CPU core.
Unlike ASMedia's USB host controllers, Promontory chips also include a PCIe switch core and a SATA host controller core, with their configuration controlled by MMIO registers in the 8051's XDATA address space.

Note: Promontory chips should not be confused with AMD's "Bixby" chipset (also called ["AMD 2019 Premium Chipset"][bixby]).
Bixby is the code name for what is marketed as the 500-series X570 chipset.
Bixby is [based on the AMD Matisse IO die on a 14nm process][x570], so it has a completely different architecture from the Promontory chips.


## Naming

"Promontory" is both the name of the chip family as well as the name of the first chip in the series.

- Promontory
  - No other qualifiers--the original chip in the series.
  - Also called:
    - "PT"
  - Marketing names:
    - A320
    - B350
    - X370
  - ASMedia identifiers:
    - Chip / Silicon Version: `0x40`
    - Firmware ID: `3306A`
- Promontory-LP
  - Also called:
    - "Low-Power Promontory"
    - "LP Promontory"
    - "LPPT"
  - Marketing names:
    - B450
    - X470
  - ASMedia identifiers:
    - Chip / Silicon Version: `0x60`
    - Firmware ID: `3306B`
- Promontory-19:
  - Also called:
    - "Promontory Plus"
    - "PT19"
    - "PROM19"
  - Marketing names:
    - A520
    - B550
  - ASMedia identifiers:
    - Chip / Silicon Version: `0x90`
    - Firmware ID: `3308A`
- Promontory-21:
  - Also called:
    - "PT21"
    - "PROM21"
  - Marketing names:
    - A620
    - B650(E)
    - X670(E)
    - B840
    - B850
    - X870(E)
  - ASMedia identifiers:
    - Chip / Silicon Version: `0xA0`
    - Firmware ID: `3328A`


## Miscellaneous Info

- Promontory
  - [55nm process][55nm]
- Promontory-LP
  - 40nm process (allegedly--it gets repeated a lot online but I haven't found a good source for this claim)


[bixby]: https://web.archive.org/web/20200715182721/https://thinkstation-specs.com/thinkstation/p620/#:~:text=AMD%202019%20Premium%20Chipset
[x570]: https://web.archive.org/web/20211005022310/https://twitter.com/IanCutress/status/1138443875154944000
[55nm]: https://web.archive.org/web/20170807124916/http://www.anandtech.com/print/10705/amd-7th-gen-bristol-ridge-and-am4-analysis-a12-9800-b350-a320-chipset#:~:text=We%20were%20informed%20that%20the%20chipsets%20are%20manufactured%20at%20TSMC%20using%20a%2055nm%20process
