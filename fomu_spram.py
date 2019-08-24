from migen import *
from fomu_6502_bus import Bus6502
class FomuSPRAM(Bus6502, Module):
    """Implements a 6502 bus interface to the ice40 UP's SPRAM.
    SPRAM is 16 bits wide_, so we need to multiplex everything in/out
    down to 8 to make good use of it."""
    
    def __init__(self, platform):
        super().__init__(platform)
        
        # 16-bit domain signals.
        self.wide_address = Signal(14)
        self.wide_datain = Signal(16)
        self.wide_dataout = Signal(16)        
        self.wide_mask = Signal(4)
        self.wide_high_half = Signal()

        self.comb += [
            self.wide_address.eq(self.address[1:]),
            self.data_out.eq(Mux(self.wide_high_half, self.wide_dataout[8:], self.wide_dataout[:8])),
            self.wide_datain.eq(Cat(self.data_in, self.data_in)),
            self.wide_mask.eq(Mux(self.wide_high_half, 0b1100, 0b0011))
            ]

        self.sync += [
            self.wide_high_half.eq(self.address[0]),
            ]
        
        self.specials += Instance("SB_SPRAM256KA",
                                      i_ADDRESS=self.wide_address,
                                      i_DATAIN=self.wide_datain,
                                      i_MASKWREN=self.wide_mask,
                                      i_WREN=self.we,
                                      i_CHIPSELECT=0b1,
                                      i_CLOCK=ClockSignal(),
                                      i_STANDBY=0b0,
                                      i_SLEEP=0b0,
                                      i_POWEROFF=0b1,
                                      o_DATAOUT=self.wide_dataout
                                      )
