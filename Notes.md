# Notes

- UART
  - 3V3
  - 921600 8N1
  - Pins:
    - RX: IC pin 10
    - TX: IC pin 11
  - Not much gets printed here, and the text that does isn't
    particularly useful.
- PCI config space
  - 0xE4: 4B, status
    - Lower 16 bits: The 8051 program counter (PC), read-only.
    - Upper 16 bits: Unknown, read-only.
  - 0xEC: 4B, control
    - Highest bit holds the 8051 and xHC in reset when set, and releases
      them from reset when cleared.
