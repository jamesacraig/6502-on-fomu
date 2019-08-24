cd build
iverilog ../testbench.v top.v /usr/local/share/yosys/ice40/cells_sim.v ../cpu.v ../ALU.v
./a.out
cd ..


