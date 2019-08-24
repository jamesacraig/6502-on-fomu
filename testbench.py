from migen.sim import run_simulation
from fomu_soc import Fomu
from fomu_platform import FomuPlatform

platform = FomuPlatform(revision="pvt")
fomu = Fomu(platform)
    
def testbench():
    yield fomu.cd_sys.clk
    yield fomu.cd_sys.rst
    yield fomu.address_bus
    yield

run_simulation(fomu, testbench())
    
