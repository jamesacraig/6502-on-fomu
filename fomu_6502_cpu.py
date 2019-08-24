import os
from migen import *
from fomu_6502_bus import Bus6502

CPU_VARIANTS=['standard']

class A6502(Bus6502, Module):
    @property
    def name(self):
        return "6502"

    @property
    def endianness(self):
        return "little"

    @property
    def gcc_triple(self):
        raise Exception("No GCC support")

    @property
    def gcc_flags(self):
        raise Exception("No GCC support")

    @property
    def linker_output_format(self):
        raise Exception("No GCC support")

    @property
    def reserved_interrupts(self):
        return {}

    def __init__(self, platform, variant="standard"):
        super().__init__(platform)
        
        self.platform = platform
        self.variant = variant
        
        # Note that we are byte-wide and so always present the
        # whole address, no byte-select lanes involved.
        self.specials += [
            Instance("cpu",
                     i_clk=ClockSignal(),
                     i_reset=ResetSignal(),
                     o_AB=self.address, 
                     o_DO=self.data_out,
                     i_DI=self.data_in,
                     o_WE=self.we,
                     i_IRQ=self.irq,
                     i_NMI=self.nmi,
                     i_RDY=self.rdy)
        ]

        platform.add_source("cpu.v")
        platform.add_source("ALU.v")
