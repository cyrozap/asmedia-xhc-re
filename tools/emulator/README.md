# Thoughts on emulator implementation


## Why write an emulator?

- Simplifies tracing
  - An emulator can show me every single instruction that gets executed
  - Breakpoints and watchpoints
  - Potential for reversible execution
- "Reverse" semihosting
  - Emulate a binary on the host PC, but forward SFR and MMIO accesses to a monitor program running on real hardware
  - Helps with mapping SFR/MMIO accesses
  - Virtual peripherals can be built based on the behavior of their real counterparts
- Enable rapid iteration in new firmware development


## Miscellaneous thoughts

- Memories:
  - ASM1042/ASM1042A/ASM1142
    - 64 kB CODE ROM
    - 64 kB CODE RAM
    - 64 kB XDATA
      - 48 kB XRAM
      - 8 kB unused
      - 8 kB MMIO
  - ASM2142/ASM3142
    - 32 kB CODE ROM
    - 96 kB CODE RAM
      - 48 kB common bank
      - 3 × 16 kB switchable banks
    - 128 kB XDATA
      - 48 kB XRAM
      - 16 kB unused
      - 64 kB MMIO
  - ASM3242
    - 32 kB CODE ROM
    - 112 kB CODE RAM
      - 48 kB common bank
      - 4 × 16 kB switchable banks
    - 128 kB XDATA
      - 48 kB XRAM
      - 16 kB unused
      - 64 kB MMIO
- Memory switching
  - All
    - CODE memory switching (ROM/RAM) on reset
    - XDATA points to CODE RAM when `PCON.MEMSEL` is set.
  - ASM2142/ASM3142 and ASM3242
    - XDATA bank switching with `DPX` (SFR 0x93)
    - CODE bank switching with `PSBANK`/`FMAP` (SFR 0x96) and jump instructions
- MMIO memory map
  - Literally each model has a different one
    - ASM1042
    - ASM1042A
    - ASM1142
    - ASM2142/ASM3142
    - ASM3242
- Should be able to pass asynchronous interrupts from external sources (e.g.,
  emulated peripherals, a real microcontroller running a monitor that forwards
  interrupts over serial to the emulator host, etc.) to the emulated core.
- Needs to be able to handle async inputs from several different sources.
  - Virtual Timer Interrupts + MMIO
  - Virtual UART Interrupts + MMIO + FIFOs
  - Virtual SPI Interrupts + MMIO + DMA
  - Virtual PCIe Interrupts + MMIO + DMA
  - (Future) Virtual USB Interrupts + MMIO + DMA
- Separate cores for pure 8051, ASM1042/ASM1042A/ASM1142, and ASM2142/ASM3142/ASM3242.
  - Pure 8051 core
    - Handles the ISA
      - All instructions can be hooked
        - Pre/post-execution
      - Each instruction execution function returns `Result<RetiredInstruction, ExitReason>`.
      - The unused 0xA5 instruction returns `ExitReason::Unimpl` if it isn't handled by a hook.
    - Receives interrupts
      - Use message interface?
    - No SFR handling beyond the ones that are absolutely necessary
      - Core SFRs:
        - SP
        - DPL
        - DPH
        - IE
        - IP
        - PSW
        - ACC
        - B
    - Performance monitoring
      - Log stats of each instruction retired
        - Instruction X was executed Y times
          - Stats for conditional jumps should indicate whether they were taken or not.
        - Start/stop counting
        - Reset stats
    - Debugging
      - Breakpoints
        - Break before execution of the instruction at the specified address.
        - Implement with CODE bus access filters?
          - CODE bus can also be accessed with MOVC, so this won't work.
      - Bus watchpoints
        - Buses that should be able to be watched:
          - CODE
          - IRAM
            - BANK[0-3]
            - Bit-addressable registers
          - SFR
          - XDATA
        - Implement with filters?
      - Reversible execution?
        - Save/restore state?
        - Generate a new state, derived from the previous state, on every instruction execution?
        - State "FIFO"?
          - FIFO with capacity for a certain number of states
            - Configurable at runtime?
            - Allowed to be infinite?
            - Disable by setting capacity to zero?
          - Once the capacity limit is reached, old states start being discarded on each new execution.
          - Before every instruction "step", a clone of the current state is pushed into the FIFO.
          - Core is initialized by setting the current state.
    - All bus accesses can be filtered
      - Pre-read
        - Arguments: `addr: MemorySpaceAddress`
        - Returns `Result<Option<u8>, ExitReason>`
      - Post-read
        - Arguments: `addr: MemorySpaceAddress, value_read: u8`
        - Returns `Result<Option<u8>, ExitReason>`
      - Pre-write
        - Arguments: `addr: MemorySpaceAddress, value_to_write: u8`
        - Returns `Result<Option<u8>, ExitReason>`
      - Post-write
        - Arguments: `addr: MemorySpaceAddress, value_written: u8`
        - Returns `Result<_, ExitReason>`
  - "Standard" 8051 core
    - Wraps pure 8051 core.
    - Implements UART, timers
      - Should timers use wall clock time or instruction-based timing?
        - Wall clock time based on specified frequency.
  - ASM1042/ASM1042A/ASM1142 core
    - Wraps pure 8051 core.
    - Handles CODE ROM/RAM switching at reset
      - Implemented as part of the `CPU_MODE_NEXT`/`CPU_MODE_CURRENT`/`CPU_EXEC_CTRL` MMIO registers?
    - Handles all "non-core" peripherals (in SFR and MMIO space)
- Loading memory
  - Load into any memory space (CODE, IRAM, SFRs, XDATA)
    - Writes to all memory spaces are treated as writes to the reset values of those memory cells
      - Each memory space has a shadow space
        - The main space contains the current values of the cells in that space
        - The shadow space contains the reset values of the cells in that space
        - The shadow space is copied to the main space when the core is reset
          - For SFRs and XDATA MMIOs, a "reset with value" method for the SFR/MMIO is called with
            the shadow space data at the corresponding address passed as an argument
          - This works for SFRs and XDATA MMIOs where the SFR/MMIO has a reset value
            - Works for SP, DPTR, SBUF, etc.
            - Doesn't work for values that are updated dynamically, like I/O port SFRs
  - Load from multiple files into arbitrary memory regions
    - Loaded in the order they were passed on the command line
    - Later writes overwrite previous writes to the same addresses
  - Both raw binary files and .ihx images should be supported
    - Both raw binary images and .ihx images support being loaded at an offset
    - The offset is zero if left unspecified
    - An error is thrown if the load ends up writing out of bounds
      - This can happen when a 64kB raw binary is loaded at a non-zero offset,
        or when the memory address in a .ihx file plus the offset is out of bounds
  - Options to fill memory
    - Fill with byte
    - Fill with zeros (default, shortcut for "fill with byte: 0")
    - Fill with 0xFF (shortcut for "fill with byte: 0xFF")
    - Fill with seeded random data
      - Random seed if not specified
      - Seed is printed when the emulator is run with this option
  - More advanced memory loading can be implemented with memory-like peripherals
  - Maybe all memory should be implemented with bus-based memory peripherals?
    - How should "bus conflicts" be handled?
- Memory aliasing
  - Some 8051 implementations have parts of XDATA mapped into CODE space to enable executing from XRAM.
  - Many 8051 implementations have parts of their memory maps "mirrored" due to simplified address decoding.
  - Maybe the emulator should be structured like real hardware, with buses connecting the memories to the CPU?
- Weird features seen in real 8051 implementations
  - Dual DPTRs
    - Auto-switching between DPTRs for, e.g., memcpy implementations.
  - DPTR auto-increment
  - Using I/O Port 2 and R0/R1 for paged access to XDATA.
  - Custom instructions
    - `0xA5` is undefined
    - Some implementations use `0xA5` as just one instruction, others use it as a prefix for multiple custom instructions.
  - SFR bank switching
- Written in Rust, with Python bindings
  - Rust for correctness and speed
  - Python for ease of scripting
    - Should be able to do all setup/initialization of the emulator (e.g., loading binaries into memory, setting register values and PC, etc.)
    - Should be able to define new core variants in Python, as well as emulated peripherals and new instructions


## Serial monitor

- Protocol
  - Binary only
  - Interrupts are disabled while transmitting/receiving data and executing commands
  - Only whole packets get received or transmitted.
  - Host doesn't send the next command until it receives the response from the command in flight.
  - Commands are at most 16 bytes long.
  - Host to device:
    - Commands:
      - Read/Write XDATA, non-critical SFRs
        - Client is responsible for not resetting the chip except through the reset command.
      - Get info
        - Chip ID
        - Chip version
        - Build date
        - Build hash
      - Reset
      - Enable/disable interrupts
      - Ping
  - Device to host:
    - Interrupt packets
      - Type: Interrupt
      - Data: Interrupt number (byte)
    - Response packets
      - Type: Response
      - Data: Response data (variable length, depends on what command it's in response to)
  - Interrupt process
    - An interrupt gets triggered
    - 8051 ISR for that interrupt executes
    - Interrupts are disabled
    - Interrupt packet is transmitted to the host
    - Interrupt flag for the triggered interrupt is cleared (if it isn't cleared by hardware)
    - Interrupts are enabled (masked with interrupt enable status)
    - Return from ISR
