from migen import *
from fomu_6502_bus import Bus6502

class SBLED(Bus6502, Module):
    def __init__(self, platform):
        super().__init__(platform)
        
        pwm_out = Signal(3) # RGB driver inputs
        pads = platform.request("led")

        # Constant-current LED driver control and RGB to output pin mapping.
        if platform.revision == "pvt" or platform.revision == "evt" or platform.revision == "dvt":
            R,G,B = 1, 0, 2
        elif platform.revision == "hacker":
            R,G,B = 2, 1, 0
            
        self.specials += Instance("SB_RGBA_DRV",
                                      i_CURREN = 1,
                                      i_RGBLEDEN = 1,
                                      i_RGB0PWM = pwm_out[R],
                                      i_RGB1PWM = pwm_out[G],
                                      i_RGB2PWM = pwm_out[B],
                                      o_RGB0 = pads.rgb0,
                                      o_RGB1 = pads.rgb1,
                                      o_RGB2 = pads.rgb2,
                                      p_CURRENT_MODE = "0b1",
                                      p_RGB0_CURRENT = "0b000011",
                                      p_RGB1_CURRENT = "0b000011",
                                      p_RGB2_CURRENT = "0b000011",
                                      )
        # LED PWM controller block.
        self.specials += Instance("SB_LEDDA_IP",
                                      i_LEDDCS = self.cs & self.we,
                                      i_LEDDCLK = ClockSignal(),
                                      i_LEDDDAT7 = self.data_in[7],
                                      i_LEDDDAT6 = self.data_in[6],
                                      i_LEDDDAT5 = self.data_in[5],
                                      i_LEDDDAT4 = self.data_in[4],
                                      i_LEDDDAT3 = self.data_in[3],
                                      i_LEDDDAT2 = self.data_in[2],
                                      i_LEDDDAT1 = self.data_in[1],
                                      i_LEDDDAT0 = self.data_in[0],
                                      i_LEDDADDR3 = self.address[3],
                                      i_LEDDADDR2 = self.address[2],
                                      i_LEDDADDR1 = self.address[1],
                                      i_LEDDADDR0 = self.address[0],
                                      i_LEDDDEN = 1,
                                      i_LEDDEXE = 1,
                                      # o_LEDDON = led_is_on, # Indicates whether LED is on or not
                                      # i_LEDDRST = ResetSignal(), # This port doesn't actually exist
                                      o_PWMOUT0 = pwm_out[0],
                                      o_PWMOUT1 = pwm_out[1],
                                      o_PWMOUT2 = pwm_out[2],
                                      o_LEDDON = Signal(),
                                      )

