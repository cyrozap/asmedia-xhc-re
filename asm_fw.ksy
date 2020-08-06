meta:
  id: asm_fw
  endian: le
  title: ASMedia xHC Firmware Image
  license: CC0-1.0
seq:
  - id: header
    size: header_len
  - id: header_checksum
    type: u1
  - id: header_crc32
    type: u4
  - id: body_len
    type:
      switch-on: magic
      cases:
        '"2114A_RCFG"': u2
        '"2214A_RCFG"': u4
  - id: body
    size: body_len
    type: body
  - id: footer
    size: 8
    type: str
    encoding: ascii
  - id: body_checksum
    type: u1
  - id: body_crc32
    type: u4
types:
  body:
    seq:
      - id: data
        size-eos: true
    instances:
      version:
        pos: 0x80
        size: 6
instances:
  magic:
    pos: 6
    size: 10
    type: str
    encoding: ascii
  header_len:
    pos: 4
    type: u2
