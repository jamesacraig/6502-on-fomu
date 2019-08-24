from migen import *
class Bus6502(object):
    """Interface for all participants on the 6502 bus.
    Used to ensure that the interface presented is consistent enough
    to allow the mux to wire them up from the memory map alone.
    """

    def __init__(self, platform):
        self.platform = platform
        self.address = Signal(16) # But your base address is subtracted, just like with wishbone.
        self.data_in = Signal(8)
        self.data_out = Signal(8)
        self.we = Signal()
        self.cs = Signal()
        self.cs_slow = Signal()
        self.irq = Signal(reset=0)
        self.nmi = Signal(reset=0)
        self.rdy = Signal(reset=1)
