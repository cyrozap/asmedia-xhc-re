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
        type: config_words
      - id: checksum
        type: u1
        doc: "A uint8 sum of all the bytes in the header, excluding the checksum and crc32."
      - id: crc32
        type: u4
        doc: "A CRC32 of all the bytes in the header, excluding the checksum and crc32."
    types:
      config_words:
        seq:
          - id: config_words
            size: 8
            type: config_word
            repeat: eos
      config_word:
        seq:
          - id: type
            type: u1
          - id: info
            size-eos: true
            type:
              switch-on: type
              cases:
                0xcc: write_data
        types:
          write_data:
            seq:
              - id: size
                type: u1
              - id: addr
                type: u2
              - id: value
                type:
                  switch-on: size
                  cases:
                    1: u1
                    2: u2
                    4: u4
  body:
    seq:
      - id: len
        type:
          switch-on: _parent.header.magic
          cases:
            '"U2104_RCFG"': u2
            '"2104B_RCFG"': u2
            '"2114A_RCFG"': u2
            '"2214A_RCFG"': u4
            '"2324A_RCFG"': u4
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
      - id: signature
        type: signature
        if: _parent.header.magic == "2324A_RCFG"
        doc: "An encrypted SHA-256 hash of body.firmware."
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
      signature:
        instances:
          encoded_start:
            pos: _root.header.len + 5 + _root.body.len + 17 + 1
            type: u1
          encoded_15180_high_nybble:
            pos: _root.header.len + 5 + _root.body.len + 17 + 2
            type: u1
          actual_start:
            value: '(encoded_start >> 1) & 0x3f'
          actual_15180_high_nybble:
            value: '(encoded_15180_high_nybble << 2) & 0xf0'
          data:
            pos: _root.header.len + 5 + _root.body.len + 17 + actual_start
            size: 0x20
