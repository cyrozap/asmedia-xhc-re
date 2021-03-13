# Notes


## Miscellaneous

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
