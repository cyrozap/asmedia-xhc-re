meta:
  id: asm_fw
  endian: le
  title: ASMedia xHC Firmware Image
  license: CC0-1.0
seq:
  - id: header
    type: header
  - id: body
    type: body
types:
  header:
    seq:
      - id: unk0
        type: u2
      - id: unk1
        type: u2
      - id: len
        type: u2
      - id: magic
        size: 10
        type: str
        encoding: ascii
      - id: data
        size: len - 16
      - id: checksum
        type: u1
        doc: "A uint8 sum of all the bytes in the header, excluding the checksum and crc32."
      - id: crc32
        type: u4
        doc: "A CRC32 of all the bytes in the header, excluding the checksum and crc32."
  body:
    seq:
      - id: len
        type:
          switch-on: _parent.header.magic
          cases:
            '"U2104_RCFG"': u2
            '"2114A_RCFG"': u2
            '"2214A_RCFG"': u4
      - id: firmware
        size: len
        type: firmware
      - id: magic
        size: 8
        type: str
        encoding: ascii
      - id: checksum
        type: u1
        doc: "A uint8 sum of all the bytes in body.firmware."
      - id: crc32
        type: u4
        doc: "A CRC32 of all the bytes in body.firmware."
    types:
      firmware:
        seq:
          - id: code
            size-eos: true
        instances:
          version:
            pos: 0x80
            size: 6
          magic:
            pos: 0x87
            size: 8
            type: str
            encoding: ascii
