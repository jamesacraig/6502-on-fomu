from migen import ClockDomain, Signal, Module, Instance, If
from migen.genlib.resetsync import AsyncResetSynchronizer

class CRG(Module):
    def __init__(self, platform, use_pll):
        clk48_raw = platform.request("clk48")
        clk12 = Signal()

        reset_delay = Signal(12, reset=4095)
        self.clock_domains.cd_por = ClockDomain()
        self.reset = Signal()

        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_usb_12 = ClockDomain()
        self.clock_domains.cd_usb_48 = ClockDomain()

        platform.add_period_constraint(self.cd_usb_48.clk, 1e9/48e6)
        platform.add_period_constraint(self.cd_sys.clk, 1e9/12e6)
        platform.add_period_constraint(self.cd_usb_12.clk, 1e9/12e6)
        platform.add_period_constraint(clk48_raw, 1e9/48e6)

        # POR reset logic- POR generated from sys clk, POR logic feeds sys clk
        # reset.
        self.comb += [
            self.cd_por.clk.eq(self.cd_sys.clk),
            self.cd_sys.rst.eq(reset_delay != 0),
            self.cd_usb_12.rst.eq(reset_delay != 0),
        ]

        if use_pll:
            # POR reset logic- POR generated from sys clk, POR logic feeds sys clk
            # reset.
            self.comb += [
                self.cd_usb_48.rst.eq(reset_delay != 0),
            ]

            self.comb += self.cd_usb_48.clk.eq(clk48_raw)

            self.specials += Instance(
                "SB_PLL40_CORE",
                # Parameters
                p_DIVR = 0,
                p_DIVF = 15,
                p_DIVQ = 5,
                p_FILTER_RANGE = 1,
                p_FEEDBACK_PATH = "SIMPLE",
                p_DELAY_ADJUSTMENT_MODE_FEEDBACK = "FIXED",
                p_FDA_FEEDBACK = 15,
                p_DELAY_ADJUSTMENT_MODE_RELATIVE = "FIXED",
                p_FDA_RELATIVE = 0,
                p_SHIFTREG_DIV_MODE = 1,
                p_PLLOUT_SELECT = "GENCLK_HALF",
                p_ENABLE_ICEGATE = 0,
                # IO
                i_REFERENCECLK = clk48_raw,
                o_PLLOUTCORE = clk12,
                # o_PLLOUTGLOBAL = clk12,
                #i_EXTFEEDBACK,
                #i_DYNAMICDELAY,
                #o_LOCK,
                i_BYPASS = 0,
                i_RESETB = 1,
                #i_LATCHINPUTVALUE,
                #o_SDO,
                #i_SDI,
            )
        else:
            self.specials += Instance(
                "SB_GB",
                i_USER_SIGNAL_TO_GLOBAL_BUFFER=clk48_raw,
                o_GLOBAL_BUFFER_OUTPUT=clk48,
            )
            self.comb += self.cd_usb_48.clk.eq(clk48)

            clk12_counter = Signal(2)
            self.sync.usb_48 += clk12_counter.eq(clk12_counter + 1)

            self.comb += clk12_raw.eq(clk12_counter[1])
            self.specials += Instance(
                "SB_GB",
                i_USER_SIGNAL_TO_GLOBAL_BUFFER=clk12_raw,
                o_GLOBAL_BUFFER_OUTPUT=clk12,
            )

        self.comb += self.cd_sys.clk.eq(clk12)
        self.comb += self.cd_usb_12.clk.eq(clk12)

        self.sync.por += \
            If(reset_delay != 0,
                reset_delay.eq(reset_delay - 1)
            )
        self.specials += AsyncResetSynchronizer(self.cd_por, self.reset)

