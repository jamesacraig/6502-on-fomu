from migen import *
from migen.genlib.fsm import FSM

from fomu_6502_bus import Bus6502

class FomuBridge(Bus6502, Module):
    def __init__(self, platform):
        super().__init__(platform)

        # Internal registers.
        self.address_reg = Signal(32)
        self.data_reg = Signal(32)

        # Wishbone signals.
        self.wishbone_adr_o = Signal(32)
        self.wishbone_dat_o = Signal(32)
        self.wishbone_dat_i = Signal(32)
        self.wishbone_ack_i = Signal()
        self.wishbone_cyc_o = Signal()
        self.wishbone_err_i = Signal()
        self.wishbone_rty_i = Signal()
        self.wishbone_sel_o = Signal()
        self.wishbone_stb_o = Signal()
        self.wishbone_we_o = Signal()

        # The wishbone address is always whatever we're given in the
        # address register.
        self.comb += [
            self.wishbone_adr_o.eq(self.address_reg)
            ]
        
        # Rule is that a write to the MSB of the data triggers a write,
        # and a read from the LSB of the data triggers a read. The other
        # bits of the data are not affected until those actions take place.
        # Bear in mind that 6502s have a bad habit of double-reads with
        # some instructions, and so care must be taken not to accidentally
        # read twice!

        # Layout of our registers is just DATA, ADDRESS, sequentially as
        # bytes in 6502-space.

        is_read_to_lsb = self.cs & (self.address == 0x00) & ~self.we
        is_write_to_msb = self.cs & (self.address == 0x03) & self.we

        # Regardless of what else you do, we always read/write from the
        # relevant registers. Because we're given CS early this can be
        # sync.
        self.sync += [
            Case(self.address, {
                0: self.data_out.eq(self.data_reg[0]),
                1: self.data_out.eq(self.data_reg[1]),
                2: self.data_out.eq(self.data_reg[2]),
                3: self.data_out.eq(self.data_reg[3]),
                4: self.data_out.eq(self.address_reg[0]),
                5: self.data_out.eq(self.address_reg[1]),
                6: self.data_out.eq(self.address_reg[2]),
                7: self.data_out.eq(self.address_reg[3])})
                ]

        # FSM to manage interaction with wishbone.
        sm = FSM(reset_state="RESET")
        self.submodules += sm
        sm.act("RESET",
                   NextValue(self.wishbone_cyc_o, False),
                   NextValue(self.wishbone_stb_o, False),
                   NextValue(self.nmi, False),
                   NextState("IDLE"))
        sm.act("IDLE",
                   If(is_read_to_lsb, NextState("START_READ")),
                   If(is_write_to_msb, NextState("START_WRITE")))
        sm.act("START_READ",
                   NextValue(self.rdy, False), # Pause the 6502.
                   NextValue(self.wishbone_cyc_o, True), # Start the wishbone cycle.
                   NextValue(self.wishbone_stb_o, True), # Trigger the strobe
                   NextValue(self.wishbone_we_o, False), # We're reading.
                   If(self.wishbone_ack_i, NextState("READ_COMPLETE")),
                   If(self.wishbone_rty_i | self.wishbone_err_i,
                          NextValue(self.nmi, True),
                          NextState("RESET"))
                   )
        sm.act("READ_COMPLETE",
                   NextValue(self.rdy, True), # Let the 6502 know we're done.
                   NextValue(self.wishbone_cyc_o, False), # Wishbone cycle complete.
                   NextValue(self.wishbone_stb_o, False), # Strobe low too.
                   NextValue(self.data_reg, self.wishbone_dat_i), # Save the read data.
                   NextState("IDLE"))
        sm.act("START_WRITE",
                   NextValue(self.rdy, False), # Tell the 6502 to wait.
                   NextValue(self.wishbone_cyc_o, True), # Start the wishbone cycle.
                   NextValue(self.wishbone_stb_o, True), # Strobe active too.
                   NextValue(self.wishbone_dat_o, self.data_reg), # Send the data.
                   If(self.wishbone_ack_i, NextState("WRITE_COMPLETE")),
                   If(self.wishbone_rty_i | self.wishbone_err_i,
                          NextValue(self.nmi, True),
                          NextState("RESET"))
                   )
        sm.act("WRITE_COMPLETE",
                   NextValue(self.rdy, True), # Let the 6502 know we're done
                   NextValue(self.wishbone_cyc_o, False), # Wishbone cycle complete
                   NextValue(self.wishbone_stb_o, False), # Strobe complete.
                   NextState("IDLE")
                   )
                   
        
