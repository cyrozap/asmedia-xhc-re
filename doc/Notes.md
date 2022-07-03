# Notes


## Miscellaneous

- CPU
  - Compatible with the MCS-51 (8051) instruction set.
  - One clock cycle per machine cycle ("1T").
    - Instruction cycle counts match the STCmicro STC15 series with the STC-Y5
      8051 core, with the exception of the MOVX instructions, which each seem
      to take between 2 and 5 clock cycles. See the instruction set summary
      starting on page 340 of [this PDF][stc] for a list of instructions and
      their cycle counts.
  - Operating frequency (high/low):
    - ASM1042, ASM1042A: 125 MHz/62.5 MHz
    - ASM1142, ASM2142/ASM3142, ASM3242: 156.25 MHz/78.125 MHz
  - IRAM size: 256 bytes
  - PMEM/CODE size:
    - ASM1042, ASM1042A, ASM1142: 64 kB
    - ASM2142/ASM3142, ASM3242: 112 kB (48 kB common bank + 4 × 16 kB banks)
  - XDATA (XRAM + MMIO) size:
    - ASM1042, ASM1042A, ASM1142: 64 kB
    - ASM2142/ASM3142, ASM3242: 128 kB (2 × 64 kB banks)
  - Bank-switching (ASM2142/ASM3142 and ASM3242 only):
    - `DPX` (SFR 0x93) is used as an extra data pointer byte for instructions
      that address memory with `DPTR` (`MOVC`, `MOVX`). Practically, however,
      because it's only a 17-bit address space only the lowest bit of `DPX` is
      used.
    - The lowest two bits of `PSBANK`/`FMAP` (SFR 0x96) are used to switch
      between code banks. The common bank is 48 kB in size and is accessible
      from 0x0000 to 0xBFFF regardless of the current value of
      `PSBANK`/`FMAP`. Banks 0-3 are each 16 kB in size and are located in
      physical code RAM at `0xC000 + 0x4000 * BANK`, where `BANK` is the index
      of the bank. All four banks are mapped at 0xC000 in PMEM/CODE space.
- UART
  - 3V3
  - 921600 8N1
  - Pins:
    - ASM1042/ASM1042A
      - RX: IC pin 14
      - TX: IC pin 15
    - ASM1142/ASM2142/ASM3142
      - RX: IC pin 10
      - TX: IC pin 11
    - ASM3242
      - RX: IC pin 15
      - TX: IC pin 16
  - Not much gets printed here, and the text that does isn't
    particularly useful.


## Feature comparison

| IC | PCI VID:DID | USB 3 Ports × Generation × Lanes | PCIe Version × Lanes | IC Package |
| --- | --- | --- | --- | --- |
| ASM1042 | 1b21:1042 | 2× Gen 1×1 | PCIe 2.x ×1 | QFN-64 |
| ASM1042A | 1b21:1142 | 2× Gen 1×1 | PCIe 2.x ×1 | QFN-64 |
| ASM1142 | 1b21:1242 | 2× Gen 2×1 | PCIe 2.x ×2 / PCIe 3.x ×1 | QFN-64 |
| ASM2142 | 1b21:2142 | 2× Gen 2×1 | PCIe 3.x ×2 | QFN-64 |
| ASM3142 | 1b21:2142 | 2× Gen 2×1 | PCIe 3.x ×2 | QFN-64 |
| ASM3242 | 1b21:3242 | 1× Gen 2×2 | PCIe 3.x ×4 | QFN-88 |


## Hardware


### ORICO PE20-1C (ASM3242)

 - Connectors
   - J7
     - 1: NC
       - Can be pulled up to 3.3V by populating restistors R54 and R351.
     - 2: GND
     - 3: 4.7k pull-up to 3.3V
       - Connected to ASM3242 pin 38 and unpopulated ASM1543 (U17) pin 27
         (`STATUS_IND2`) by unpopulated resistor R353.
     - 4: 4.7k pull-up to 3.3V
       - Connected to ASM3242 pin 37 and unpopulated ASM1543 (U17) pin 26
         (`STATUS_IND1`) by unpopulated resistor R352.
   - J4
     - 1: NC
       - Can be pulled up to 3.3V by populating restistors R54 and R85.
     - 2: GND
     - 3: TX
       - Connected to ASM3242 pin 16.
     - 4: RX - 1k pull-up to 3.3V
       - Connected to ASM3242 pin 15.
   - J1
     - 4: NC
     - 3: NC
     - 2: GND
     - 1: GND
 - LEDs
   - LED1
     - Power.
   - LED2
     - Cable connected.
   - LED4 (unpopulated)
     - Connected to ASM3242 pin 17.
     - Signal is also available on one of the three testpoints in a cluster
       near the ASM3242.
   - LED5 (unpopulated)
     - Connected to ASM3242 pin 18.
     - Signal is also available on one of the three testpoints in a cluster
       near the ASM3242.
   - LED6 (unpopulated)
     - Connected to ASM3242 pin 19.
     - Signal is also available on one of the three testpoints in a cluster
       near the ASM3242.
   - LED7 (unpopulated)
     - Connected to ASM3242 pin 39 by unpopulated resistor R357.
   - LED8 (unpopulated)
     - Connected to ASM3242 pin 43 by resistor R359.
   - LED9 (unpopulated)
     - Connected to ASM3242 pin 44 by resistor R360.


### IOCrest IO-PCE3242-1C (ASM3242)

 - Voltage rails
   - 3V3 (I/O)
   - 2V5 (Analog?)
   - 1V05 suspend (SRAM?)
   - 1V05 (Core?)
 - Components
   - ICs:
     - U6: [TD6817][td6817] 1.5MHz 2A Synchronous Step-Down Regulator Dropout
   - Capacitors:
     - C69: 10 pF, 10% (measured value: 11 pF)
     - C72: 100 nF, 20% (measured value: 123 nF)
   - Inductors:
     - L2: ??? H, 0.2 Ω
   - Resistors:
     - R44: 100 kΩ
     - R47: 75 kΩ (measured value: 74.4 kΩ)


[stc]: https://web.archive.org/web/20200305112930/http://stcmicro.com/datasheet/STC15F2K60S2-en.pdf
[td6817]: https://web.archive.org/web/20220401041252if_/http://techcodesemi.com/datasheet/TD6817.pdf
