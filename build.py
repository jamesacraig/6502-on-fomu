import os
import sys
import argparse

VERSION_MAJOR = 0
VERSION_MINOR = 1

# Parse arguments first, so --version works even if the deps misbehave.
parser = argparse.ArgumentParser(description="Build Fomu bitstream")
parser.add_argument(
    "--revision", choices=["evt", "dvt", "pvt", "hacker"], required=True,
    help="Hardware revision to target"
    )
parser.add_argument(
    "--version",
    action="version",
    version=str(VERSION_MAJOR)+"."+str(VERSION_MINOR),
    help="Show current version")
parser.add_argument(
    "--test",
    action="store_true",
    help="Run as testbench")
args = parser.parse_args()

# Add all the dependencies' base paths into the Python path.
base_dir = os.path.dirname(__file__)
deps_dir = os.path.join(base_dir, "deps")
for dep in os.listdir(deps_dir):
    sys.path.append(os.path.join(deps_dir, dep))

from fomu_platform import FomuPlatform
from fomu_soc import Fomu

platform = FomuPlatform(revision = args.revision)
soc = Fomu(platform)

if not args.test:
    output_dir = os.path.join(base_dir, "build")
    platform.build(soc)
else:
    from migen.sim import run_simulation
    def testbench():
        yield soc.cd_sys.clk
        yield soc.cd_sys.rst
        yield soc.address_bus
        yield
    
    run_simulation(soc, testbench())
