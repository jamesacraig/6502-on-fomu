from migen import *
from fomu_6502_bus import Bus6502
from random import randint

class FomuROM(Bus6502, Module):
    def __init__(self, platform):
        super().__init__(platform)
        rom_bytes = [
            # Boot rom, starts at 0xFF00
            0xA9, 0b10000000,  # LDA #&80
            0x8D, 0x08, 0xFE,  # STA &FE08   - LEDDCR0
            0xA9, 187,         # LDA #187
            0x8D, 0x09, 0xFE,  # STA &FE09   - LEDDBR0
            0xA9, 0x40,        # LDA #&40
            0x8D, 0x10, 0xFE,  # STA &FE10   - LEDDONR
            0x8D, 0x10, 0xFE,  # STA &FE10   - LEDDOFR
            0xA9, 0x00,        # LDA #&00
            0x8D, 0x05, 0xFE,  # STA &FE05   - LEDDBCRR
            0x8D, 0x06, 0xFE,  # STA &FE06   - LEDDBCFR
            0xA9, 0xFF,        # LDA #&FF
            0x8D, 0x00, 0x00,  # STA #&0000 - Save FF to RAM address 0
            0xA9, 0x00,        # LDA #&00
            0x8D, 0x01, 0x00,  # STA #&0001 - Save 00 to RAM address 1
            0xAD, 0x00, 0x00,  # LDA &0000  - Load from RAM address 0
            0x8D, 0x01, 0xFE,  # STA &FE01  - LEDDPWRR
            0xAD, 0x01, 0x00,  # LDA &0001  - Load from RAM address 1
            0x8D, 0x02, 0xFE,  # STA &FE02  - LEDDPWRG
            0x8D, 0x03, 0xFE   # STA &FE03  - LEDDPWRB
        ]

        while len(rom_bytes) < 250:
            rom_bytes = rom_bytes + [0x00]

        # Set up all vectors to point to 0xFF00
        rom_bytes += [
            0x00, 0xFF,
            0x00, 0xFF,
            0x00, 0xFF
            ]

        byte_map = {i:self.data_out.eq(rom_bytes[i]) for i in range(256)}
        self.sync += [Case(self.address, byte_map)]
            
