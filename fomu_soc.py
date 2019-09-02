from collections import namedtuple
from fomu_clock import CRG
from fomu_6502_cpu import A6502
from fomu_6502_rgb import SBLED
from fomu_spram import FomuSPRAM
from fomu_6502_rom import FomuROM
from fomu_6502_wishbone_bridge import FomuBridge
from fomu_usb_cdc import FomuUSBCDC
from migen import *

AddressRange = namedtuple("AddressRange", ("start", "size"))

# The 6502 processor is too different to what litex expects to see. In particular,
# the address space for the various CSRs is much smaller than would be normal, and
# we want to be able to handle system features like banked RAM etc.
# As a result we can't use AutoCSR and friends directly. The Fomu class below is what
# might in other circumstances represent a normal litex SoCCore subclass.
class Fomu(Module):
    """Basic SoC class for a 6502-based Fomu core."""
    # We emulate roughly the memory map of a BBC Micro here. This isn't for any particularly
    # good reason; it's just one that has reasonable expectations and which provides
    # a decent model to work from.
    memory_map = {
        "ram": AddressRange( 0x0, 0x8000),
        "paged_rom": AddressRange( 0x8000, 0x4000),
        "low_os_rom": AddressRange( 0xC000, 0x3c00),
        "rgb": AddressRange(0xFE00, 0x10),
        "wishbone": AddressRange(0xFE20, 0x08), 
        "paging_register": AddressRange(0xFE30, 0x10),
        "high_os_rom": AddressRange(0xFF00, 0xFF),
        }

    def __init__(self, platform):
        # Set up the basic address space layout and create basic
        # select signals for each entry in the memory map.
        self.address_bus = Signal(16)
        for name, address_range in self.memory_map.items():
            fast_sel = Signal(name=name+"_sel")
            slow_sel = Signal(name=name+"_sel_slow")
            setattr(self, name+"_sel", fast_sel)
            setattr(self, name+"_sel_slow", slow_sel)
            self.comb += [
                fast_sel.eq(Mux(wrap(self.address_bus >= address_range.start) & wrap(self.address_bus < address_range.start+address_range.size), 1, 0))
            ]
            # Latched versions, needed to drive the databus logic
            self.sync += [
                slow_sel.eq(Mux(wrap(self.address_bus >= address_range.start) & wrap(self.address_bus < address_range.start+address_range.size), 1, 0))
            ]

        # Fomu clock/reset generator, using the PLL to generate a 48MHz and 12MHz clock.
        # The 12MHz clock becomes cd_sys; the 48MHz clock is available as cd_usb_48.
        self.submodules.crg = CRG(platform, use_pll=True)

        #self.clock_domains.cd_sys = ClockDomain()
        #clk48_raw = platform.request("clk48")
        #platform.add_period_constraint(clk48_raw, 1e9/48e6)
        #self.startup_delay = Signal(12, reset=4095)
        #self.comb += [self.cd_sys.clk.eq(clk48_raw),
        #    self.cd_sys.rst.eq(self.startup_delay!=0)]
        #self.sync += [
        #    If(self.startup_delay==0,self.startup_delay.eq(0)).Else(self.startup_delay.eq(self.startup_delay-1))
        #    ]
        #self.clk_freq = 48000000
        # Output the reset to avoid some trimming.
        #self.comb += [
        #    platform.request("usb").d_p.eq(self.cd_sys.rst)
        #    ]
        
        # CPU
        self.submodules.cpu = A6502(platform)
        
        # Basic RAM.
        self.submodules.ram = FomuSPRAM(platform)

        # Boot ROM (for debug only)
        self.submodules.high_os_rom = FomuROM(platform)

        # LEDs for I/O
        self.submodules.rgb = SBLED(platform)

        # Wishbone bridge
        self.submodules.wishbone = FomuBridge(platform)
        
        # Build up a mux for the data bus (in), IRQ, NMI, RDY, and connect up the chip selects.
        mux = Constant(0)
        rdy_mux = Constant(1)
        irq_mux = Constant(0)
        nmi_mux = Constant(0)
        
        for name, address_range in self.memory_map.items():
            try:
                # Find the module and its select signals
                module = getattr(self, name)
            except AttributeError:
                print("Warning: Memory map defines \'"+name+"\' but no submodule exists.")
                continue
            select_fast = getattr(self, name+"_sel")
            select_slow = getattr(self, name+"_sel_slow")
            
            # Extend the existing muxes for this module. Slow select used for mux
            # because this CPU core reads one cycle behind the address bus.
            mux = Mux(select_slow, module.data_out, mux)
            rdy_mux = Mux(select_slow, module.rdy, rdy_mux)
            irq_mux = irq_mux | module.irq
            nmi_mux = nmi_mux | module.nmi
            
            self.comb += [
                # Connect up the CS signals.
                module.cs.eq(select_fast),
                module.cs_slow.eq(select_slow),
                # Wire up the address bus in to each device too.
                module.address.eq(self.address_bus - address_range.start),
                # And the data bus out to it.
                module.data_in.eq(self.cpu.data_out),
                module.we.eq(self.cpu.we)
                ]
                
            print("Connected device",name,"at",address_range)
                
        print("Constructed data mux:", mux)
        print("Constructed RDY mux:", rdy_mux)
        self.comb += [self.cpu.data_in.eq(mux),
                          self.cpu.rdy.eq(rdy_mux),
                          self.cpu.irq.eq(irq_mux),
                          self.cpu.nmi.eq(nmi_mux),
                          self.address_bus.eq(self.cpu.address)]


        # Set up a dummyusb device.
        from valentyusb.usbcore import io as usbio
        usb_pads = platform.request("usb")
        usb_iobuf = usbio.IoBuf(usb_pads.d_p, usb_pads.d_n, usb_pads.pullup)
        self.submodules.usb = FomuUSBCDC(usb_iobuf)
        
