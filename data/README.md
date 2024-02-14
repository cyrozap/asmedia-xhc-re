# Data

`brom_info.csv` lists the known versions, sizes, and checksums of the boot ROMs
(BROMs) of each chip. The "CRC-32 (Embedded)" values listed in the file are the
CRC-32 values included in the BROMs themselves, while the cryptographic hashes
are calculated over all the bytes in the BROMs--including the CRC-32 values. In
other words, the CRC-32 is calculated over the first `Size - 4` bytes of each
BROM, while the hashes are calculated over the first `Size` bytes.

The `regs-asmXXXX.yaml` files contain the memory maps and register definitions
for the chips. They are used as inputs into the documentation generator.

To generate documentation, run `make doc` in the parent directory.
